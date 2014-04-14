import os

from oslo.config import cfg

from bricks.common import opencrack
from bricks.common import states
from bricks.common import utils as common_utils
from bricks.common.utils import JinjaMailTemplate as T
from bricks.db import api as dbapi
from bricks.openstack.common import log

from novaclient import exceptions as nova_exceptions

LOG = log.getLogger(__name__)

conductor_utils_opts = [
    cfg.StrOpt('image_uuid',
               default='8b20af24-1946-4fe5-a7c3-ad908c684712',
               help='Instance image UUID'),
]

CONF = cfg.CONF
CONF.register_opts(conductor_utils_opts, 'conductor_utils')


##
# Actions
def brick_deploy_action(req_context, brick_id):
    """Deploy a brick task called from the manageer.

    :param req_context:
    :param brick_id:
    """

    db = dbapi.get_instance()
    brick = db.get_brick(brick_id)
    brickconfig = db.get_brickconfig(brick.brickconfig_uuid)

    server_id = _deploy_nova_server(
        req_context,
        brick,
        brickconfig)

    # return an instance ID to assoc the brick
    brick.instance_id = server_id
    brick.status = states.INIT
    brick.save(req_context)


def brick_deploying_action(req_context, brick_id):
    """Brick has reached deploying state.
    """

    db = dbapi.get_instance()
    brick = db.get_brick(brick_id)

    brick.status = states.DEPLOYING
    brick.save(req_context)

    # Reset instance state
    LOG.debug('Resetting instance state %s' % brick.instance_id)
    try:
        opencrack.api_request('compute', 'admin',
                              None, '/servers/%s/action' % brick.instance_id,
                              {"os-resetState": {"state": "active"}})
    except Exception, e:
        LOG.warning('Unable to set %s to active' % brick.instance_id,
                    e.message)


def brick_deployfail_action(req_context, brick_id):
    """Brick has failed to deploy
    """

    db = dbapi.get_instance()
    brick = db.get_brick(brick_id)

    brick.status = states.DEPLOYFAIL
    brick.save(req_context)


def brick_deploydone_action(req_context, brick_id):
    """Brick has completed deploying
    """

    db = dbapi.get_instance()
    brick = db.get_brick(brick_id)
    floating_ip = brick.configuration.get("floating_ip")

    if floating_ip:
        _drive_floating_ip(req_context, brick, floating_ip)
    brick.status = states.DEPLOYDONE
    brick.save(req_context)


def brick_destroy_action(req_context, brick_id):
    """Destroy a brick!
    """

    db = dbapi.get_instance()
    brick = db.get_brick(brick_id)

    try:
        _destroy_nova_server(req_context, brick.instance_id)
    except nova_exceptions.NotFound:
        pass

    db.destroy_brick(brick_id)


def deleted_instances_cleanup_action(req_context):
    """checks nova API for instance UUIDs of all instances to compare
    against what we're tracking. If nova doesn't track one of the
    instances, we should delete the associated brick so it doesn't get
    cluttered up.

    :param req_context: admin request context
    """
    LOG.debug("Cleaning up bricks that fell out of sync with instances")

    # get all bricks
    db = dbapi.get_instance()
    bricks = db.get_brick_list()
    LOG.debug("Have %s bricks" % len(bricks))

    # get all nova instances
    novaclient = opencrack.build_nova_client(req_context)
    novaclient.authenticate()
    servers = novaclient.servers.list()
    server_uuids = [server.id for server in servers]
    LOG.debug("Have %s instances" % len(server_uuids))

    # generate a list of bricks whose instance_ids don't show up in the
    # nova list
    bricks_to_clean = []
    for brick in bricks:
        if brick.instance_id and brick.instance_id not in server_uuids:
            # brick has an instance record, but nova is not reporting
            # as being there.
            bricks_to_clean.append(brick)

    LOG.debug("Have %s bricks to clean up" % len(bricks_to_clean))

    # delete the bricks in that list
    for brick in bricks_to_clean:
        LOG.debug("Destroying unused brick %s for instance %s" % (
            brick.id, brick.instance_id))
        db.destroy_brick(brick.id)


##
# Action actions
def _deploy_nova_server(req_context, brick, brickconfig):
    """Deploy the server using nova
    """

    # Ubuntu ONLY, image is hard coded.
    image = CONF.conductor_utils.image_uuid

    # Create our required security group if needed
    sec_groups = ensure_security_groups(req_context, brickconfig)

    nic = [{"net-id": brick.configuration['network'],
            "v4-fixed-ip": ""}]

    novaclient = opencrack.build_nova_client(req_context)
    novaclient.authenticate()
    server = novaclient.servers.create(
        brick.configuration['name'],
        image,
        brick.configuration['flavour'],
        userdata=get_userdata(),
        config_drive=True,
        disk_config='AUTO',
        key_name=brick.configuration['keypair'],
        nics=nic,
        security_groups=sec_groups)

    return server.id


def _destroy_nova_server(req_context, instance_id):
    """Destroys nova instance
    """

    novaclient = opencrack.build_nova_client(req_context)
    novaclient.servers.delete(instance_id)


def get_userdata():
    userdata_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 "../common/nova_userdata.sh")
    return open(userdata_path, 'r')


def ensure_security_groups(req_context, brickconfig):
    """Ensure a security group is created or already exists for the user
    under the name, and make sure it has the correct ports open.

    :param req_context: populated request context
    :param brickconfig: brickconfig with port configuration
    """

    g_id = []
    exists = False

    sec_groups = opencrack.api_request(
        'compute', req_context.auth_token, req_context.tenant_id,
        '/os-security-groups', method='GET'
    ).json()

    for group in sec_groups['security_groups']:
        if group['name'] == u"%s" % brickconfig.name:
            exists = True
            g_id.append(group['id'])
            break

    if not exists:
        # if it doesn't exist, create it and make sure all the ports are bound.
        sec_group_data = {
            'security_group': {
                'name': brickconfig.name,
                'description': 'Auto-generated security group for %s' % brickconfig.name
            }
        }
        sec_group = opencrack.api_request(
            'compute', req_context.auth_token, req_context.tenant_id,
            '/os-security-groups', data=sec_group_data
        ).json().get('security_group')

        g_id.append(sec_group['id'])

        for port in brickconfig.ports:
            port_data = {
                'security_group_rule': {
                    'ip_protocol': 'tcp',
                    'from_port': port,
                    'to_port': port,
                    'cidr': '0.0.0.0/0',
                    'parent_group_id': sec_group['id'],
                    'group_id': None
                }
            }
            opencrack.api_request(
                'compute', req_context.auth_token, req_context.tenant_id,
                '/os-security-group-rules', data=port_data)

    return g_id


def _drive_floating_ip(req_context, brick, floating_ip):
    """Execute assigning the floating IP!
    """

    action = {'addFloatingIp': {'address': floating_ip}}
    action_url = '/servers/%s/action' % brick.instance_id

    opencrack.api_request('compute',
                          req_context.auth_token,
                          req_context.tenant_id,
                          action_url,
                          action)


def notify_completion(req_context, brick, brickconfig):
    """Notify anyone who needs to know, however tehy need to know it that an
    instance is completeNotify anyone who needs to know, however tehy need
    to know it that an instance is complete.

    Args:
        brick
    """
    # get email address
    email_address = brick.configuration.get('notification_address',
                                            'info@clouda.ca')

    # send the notification to the user
    send_admin_notification(brick, brickconfig)
    send_installation_notification(email_address, brick, brickconfig)


def send_installation_notification(email, brick, brickconfig):
    """Send the user who installed the Dockerstack app an email notifying them
    that the installation is complete, and tells them anything extra they
    need to know about configuring or logging into the system.

    :param email:
    :param brick:
    :param brickconfig:
    """

    tpl = T(brickconfig.email_template)
    ctx = {
        'brick': brick,
        'config': brickconfig
    }
    body = tpl.render(**ctx)

    common_utils.send_mandrill_mail_api(
        to=[(email, email, ), ],
        subject="Your brick is laid",
        text=body,
        sender=("support@clouda.ca", "CloudA Brick Notifier"))


def send_admin_notification(brick, brickconfig):
    """Notify us that a brick has been installed.

    :param brick:
    :param brickconfig:
    """
    LOG.warning("Brick %s installed" % brickconfig.name,
                extra={'stack': True})


def do_task_report(results):
    """Records task results, and does things with them: updates state or
    what have you

    :param results: [MortarTaskResult, ]
    """
    for result in results:
        if not result.test_result:
            LOG.warning(
                "Something Failed for instance %s, %s" % (
                    result.instance_id, result.message))
    pass


def render_config_file(configfile, brick, brickconfig):
    """Render a configfile template using the appropriate configuration
    and variables loaded from the brick env and brickconfig.
    """
    tpl = T(configfile.contents)
    return tpl.render(brick=brick, brickconfig=brickconfig)
