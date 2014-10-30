import json
import requests

from oslo.config import cfg

from keystoneclient.v2_0 import client as keystone_client
from novaclient.v1_1 import client as nova_client

from bricks.openstack.common import log

logger = log.getLogger(__name__)

CONF = cfg.CONF
CONF.import_group('keystone_authtoken', 'keystoneclient.middleware.auth_token')


def build_nova_client(req_context):
    if req_context.auth_token == 'admin' and req_context.tenant is None:
        username = CONF.keystone_authtoken.admin_user
        password = CONF.keystone_authtoken.admin_password
        tenant_name = CONF.keystone_authtoken.admin_tenant_name
    else:
        username = req_context.user
        password = req_context.auth_token
        tenant_name = req_context.tenant

    c = nova_client.Client(username,
                           password,
                           project_id=tenant_name,
                           auth_url=CONF.keystone_authtoken.auth_uri,
                           endpoint_type='internalURL',
                           insecure=False)

    if req_context.auth_token != 'admin':
        c.client.auth_token = req_context.auth_token

    return c


def build_keystone_client(token_id):
    if token_id == 'admin':
        return keystone_client.Client(
            endpoint=CONF.keystone_authtoken.auth_uri)
    else:
        return keystone_client.Client(
            token=token_id, endpoint=CONF.keystone_authtoken.auth_uri)


def get_keystone_token(keystone_client, token_id, tenant_id):
    if token_id == 'admin' and tenant_id is None:
        return keystone_client.tokens.authenticate(
            username=CONF.keystone_authtoken.admin_user,
            password=CONF.keystone_authtoken.admin_password,
            tenant_name=CONF.keystone_authtoken.admin_tenant_name)
    else:
        return keystone_client.tokens.authenticate(token=token_id,
                                                   tenant_id=tenant_id)


def api_request(catalog_type, token_id, tenant_id, url, data=None,
                method='POST'):
    """Manual Openstack API wrapper since some of the clients suck, and can't
    do what we want them to.

    Args:
        catalog_type (string) - The type of api request we want to make
                     (compute, keystone, etc) by service name.
        token_id (string) - The token ID to use, will re-auth through keystone.
        tenant_id (string)
        url (string) - the path portion of the url that wants to be called.
        data (dict) - A dict of data that will get JSON dumped. if None is
                      passed, it's dropped completely.
        method (string) - HTTP Method, GET | POST

    Returns (requests.Response)
    """
    ksc = build_keystone_client(token_id)
    token = get_keystone_token(ksc, token_id, tenant_id)

    headers = {
        'X-Auth-Token': token.id,
        'content-type': 'application/json'
    }

    endpoint = None

    # find the service in the token's catalog
    for service in token.serviceCatalog:
        if service["type"] == catalog_type:
            endpoint = service["endpoints"][0]["internalURL"]

    # Use requests to post to the API url, since the nova client blows
    server_url = "%s%s" % (endpoint, url)
    if data:
        resp = requests.request(method, server_url, headers=headers,
                                data=json.dumps(data))
    else:
        resp = requests.request(method, server_url, headers=headers)

    logger.info(resp.text)
    return resp
