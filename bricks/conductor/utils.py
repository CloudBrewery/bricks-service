import json

import emails
from emails.template import JinjaTemplate

from bricks.common import opencrack
from bricks.db import api as dbapi
from bricks.openstack.common import log

LOG = log.getLogger(__name__)

BRICKS_URL = 'https://dash-dev.clouda.ca/dockerstack/update'


def deploy_nova_server(name, image, flavour, **kwargs):
    """Deploy the server using nova
    """
    nova_client = api.nova.novaclient(request)
    server = nova_client.servers.create(name, image, flavour, **kwargs)
    return server.id


def get_userdata():
    # load the bootfile for passing to the server on create.
    import dockerstack_agent.bootfile
    userdata_path = dockerstack_agent.bootfile.path()
    return open(userdata_path, 'r')


def ensure_secugirty_groups(req_context, brickconfig):
    """Ensure a security group is created or already exists for the user
    under the name, and make sure it has the correct ports open.
    """
    return True

    sec_groups = create_instance.assign_security_groups(
        request,
        override_name=config.get("name"),
        port_list=config.get("ports")
    )


def get_tgz_downloads(brickconfig):

    tgz_download = [app_settings.DOCKERSTACK_BRICKINIT, ]
    for dep in brickconfig.dockerstack_url:
        tgz_download.append(dep)
    tgz_download.append(app_settings.DOCKERSTACK_BRICKDONE)

    return tgz_download


def prepare_instance_meta(req_context, brick, brickconfig):
    tgz_download = get_tgz_downloads(brickconfig)

    meta = {
        'brick_name': brickconfig.name,
        'dockerstack_download': app_settings.DOCKERSTACK_APP_REPO,
        'dockerstack_repo': json.dumps(tgz_download)
    }

    tmp = {
        'BRICKS_URL': BRICKS_URL,
        'TOKEN_ID': req_context.auth_token.id,
    }

    for k, v in tmp.items():
        meta['_tmp_' + k] = v

    for k, v in brick.configuration.items():
        meta['_env_' + k] = v

    return meta


def brick_deploy_action(req_context, brick_id):
    """Deploy a brick!

    Args:
        task_context:
    """
    db = dbapi.get_instance()
    brick = db.get_brick(brick_id)
    brickconfig = db.get_brickconfig(brick.brickconfig_uuid)

    # Ubuntu ONLY, image is hard coded.
    image = '8b20af24-1946-4fe5-a7c3-ad908c684712'

    # Create our required security group if needed
    sec_groups = ensure_secugirty_groups(req_context, brickconfig)
    meta = prepare_instance_meta(req_context, brick, brickconfig)

    nic = [{"net-id": brick.configuration['network'],
            "v4-fixed-ip": ""}]

    server_id = deploy_nova_server(
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

    # return an instance ID to assoc the brick?
    brick.instance_id = server_id
    brick.save(req_context)


def brick_destroy_action(req_context, brick_id):
    """"Destroy a brick!
    """
    pass


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
