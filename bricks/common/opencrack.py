import json
import requests

from keystoneclient.v2_0 import client as keystone_client
from novaclient.v1_1 import client as nova_client

from bricks.common import keystone
from bricks.openstack.common import log

logger = log.getLogger(__name__)


def build_nova_client(req_context):
    c = nova_client.Client(req_context.user,
                           req_context.auth_token,
                           project_id=req_context.tenant,
                           auth_url=keystone.get_service_url('compute'),
                           insecure=False)
    c.client.auth_token = req_context.auth_token
    c.client.management_url = keystone.get_service_url('compute')
    return c


def build_keystone_client(token_id):
    return keystone_client.Client(token=token_id,
                                  endpoint=keystone.get_service_url(
                                      'keystone'))


def get_keystone_token(keystone_client, token_id, tenant_id):
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
            endpoint = service["endpoints"][0]["publicURL"]

    # Use requests to post to the API url, since the nova client blows
    server_url = "%s%s" % (endpoint, url)
    if data:
        resp = requests.request(method, server_url, headers=headers, data=json.dumps(data))
    else:
        resp = requests.request(method, server_url, headers=headers)

    logger.info(resp.text)
    return resp
