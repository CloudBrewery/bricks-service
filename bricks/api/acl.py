# -*- encoding: utf-8 -*-

"""Access Control Lists (ACL's) control access the API server."""

from keystoneclient.middleware import auth_token as keystone_auth_token
from oslo.config import cfg

from bricks.api.middleware import auth_token


OPT_GROUP_NAME = 'keystone_authtoken'


def register_opts(conf):
    """Register keystoneclient middleware options

    :param conf: Ironic settings.
    """
    conf.register_opts(keystone_auth_token.opts, group=OPT_GROUP_NAME)
    keystone_auth_token.CONF = conf


def install(app, conf, public_routes):
    """Install ACL check on application.

    :param app: A WSGI applicatin.
    :param conf: Settings. Must include OPT_GROUP_NAME section.
    :param public_routes: The list of the routes which will be allowed to
                          access without authentication.
    :return: The same WSGI application with ACL installed.

    """
    register_opts(cfg.CONF)
    keystone_config = dict(conf.get(OPT_GROUP_NAME))
    return auth_token.AuthTokenMiddleware(app,
                                          conf=keystone_config,
                                          public_api_routes=public_routes)
