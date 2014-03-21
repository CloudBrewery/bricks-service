import json

import emails
from emails.template import JinjaTemplate

from bricks.common import exception
from bricks.common import opencrack
from bricks.common import states
from bricks.db import api as dbapi
from bricks.openstack.common import log

from novaclient import exceptions as nova_exceptions

LOG = log.getLogger(__name__)

BRICKS_URL = 'https://dash-dev.clouda.ca/dockerstack/update'


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
    image = '8b20af24-1946-4fe5-a7c3-ad908c684712'

    # Create our required security group if needed
    sec_groups = ensure_security_groups(req_context, brickconfig)
    meta = prepare_instance_meta(req_context, brick, brickconfig)

    nic = [{"net-id": brick.configuration['network'],
            "v4-fixed-ip": ""}]

    novaclient = opencrack.build_nova_client(req_context)
    server = novaclient.servers.create(
        brickconfig.name,
        image,
        brick.configuration['flavour'],
        meta=meta,
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
    # load the bootfile for passing to the server on create.
    import dockerstack_agent.bootfile
    userdata_path = dockerstack_agent.bootfile.path()
    return open(userdata_path, 'r')


def ensure_security_groups(req_context, brickconfig):
    """Ensure a security group is created or already exists for the user
    under the name, and make sure it has the correct ports open.
    """

    g_id = []
    exists = False

    novaclient = opencrack.build_nova_client(req_context)
    sec_groups = novaclient.security_groups.list()

    for group in sec_groups:
        if group.name == u"%s" % brickconfig.name:
            exists = True
            g_id.append(group.id)
            break

    if not exists:
        # if it doesn't exist, create it and make sure all the ports are bound.
        sec_group = novaclient.security_groups.create(
            brickconfig.name,
            "Auto-generated security group for %s" % brickconfig.name)

        g_id.append(sec_group.id)

        for port in brickconfig.ports:
            novaclient.security_group_rules.create(
                sec_group.id,
                'tcp',
                port,
                port,
                '0.0.0.0/0',
                None)

    return g_id


def get_tgz_downloads(brickconfig):
    """Literally

    """
    tgz_download = [app_settings.DOCKERSTACK_BRICKINIT, ]
    for dep in brickconfig.dockerstack_url:
        tgz_download.append(dep)
    tgz_download.append(app_settings.DOCKERSTACK_BRICKDONE)

    return tgz_download


def prepare_instance_meta(req_context, brick, brickconfig):
    """Prepares a set of metadata to get injected into an instance while the
    deploy is happening so Dockerstack can initialize fully.

    """

    meta = {}

    tmp = {
        'BRICKS_API': BRICKS_URL,
        'BRICKS_UUID': brick.uuid,
        'TOKEN_ID': req_context.auth_token.id,
    }

    for k, v in tmp.items():
        meta['_tmp_' + k] = v

    return meta


def _drive_floating_ip(req_context, brick, floating_ip):
    """Execute assigning the floating IP!
    """

    action = {'addFloatingIp': {'address': floating_ip}}
    action_url = '/servers/%s/action' % brick.instance_id

    opencrack.api_request('compute',
                          req_context.auth_token.id,
                          req_context.auth_token.tenant_id,
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

    # get the instance details
    instance_response = opencrack.api_request(
        'compute',
        req_context.auth_token.id,
        req_context.auth_token.tenant_id,
        '/servers/%s' % brick.instance_id, method='GET')

    server_details = instance_response.json()['server']
    meta = server_details['metadata']

    # send the notification to the user
    send_installation_notification(email_address, brickconfig, meta)
    send_admin_notification(brickconfig, meta)


def send_installation_notification(email, brickconfig, meta):
    """Send the user who installed the Dockerstack app an email notifying them
    that the installation is complete, and tells them anything extra they
    need to know about configuring or logging into the system.

    Args:
        email (string) - .
        configuration (dict) - the application config from app_settings that
                            was installed.
        meta (dict) - the information that was fed to the server's metadata
    """
    message = emails.html(text=JinjaTemplate(brickconfig.email_template),
                          subject="Your brick is laid",
                          mail_from="support@clouda.ca")

    ctx = {
        'meta': meta,
        'config': brickconfig
    }
    message.send(to=email, render=ctx)


def send_admin_notification(configuration, meta):
    """Notify us that a brick has been installed."""
    LOG.warning("Brick %s installed" % configuration['name'],
                extra={'stack': True})


def do_task_report(results):
    """Records task results, and does things with them: updates state or
    what have you

    :param results: [MortarTaskResult, ]
    """
    pass
