# -*- encoding: utf-8 -*-

from oslo.config import cfg

# Server Specific Configurations
# See https://pecan.readthedocs.org/en/latest/configuration.html#server-configuration # noqa
server = {
    'port': '8119',
    'host': '0.0.0.0'
}

# Pecan Application Configurations
# See https://pecan.readthedocs.org/en/latest/configuration.html#application-configuration # noqa
app = {
    'root': 'bricks.api.controllers.root.RootController',
    'modules': ['bricks.api'],
    'static_root': '%(confdir)s/public',
    'debug': True,
    'enable_acl': True,
    'acl_public_routes': ['/', '/v1'],
}

# WSME Configurations
# See https://wsme.readthedocs.org/en/latest/integrate.html#configuration
wsme = {
    'debug': cfg.CONF.debug,
}
