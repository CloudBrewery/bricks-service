import os

from oslo.config import cfg

import emails
from emails.template import JinjaTemplate as T

from bricks.common import opencrack
from bricks.common import states
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
                          req_context.tenant,
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
    email_address = req_context.user.username

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

    message = emails.html(text=T(brickconfig.email_template),
                          subject="Your brick is laid",
                          mail_from="support@clouda.ca")
    ctx = {
        'brick': brick,
        'config': brickconfig
    }

    message.send(to=email, render=ctx)


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
