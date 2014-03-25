# -*- encoding: utf-8 -*-

from oslo.config import cfg
import pecan

from bricks.api import acl
from bricks.api import config
from bricks.api import hooks
from bricks.api import middleware
from bricks.common import policy

auth_opts = [
    cfg.StrOpt('auth_strategy',
        default='keystone',
        help='Method to use for authentication: noauth or keystone.'),
]

CONF = cfg.CONF
CONF.register_opts(auth_opts)


def get_pecan_config():
    # Set up the pecan configuration
    filename = config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def setup_app(pecan_config=None, extra_hooks=None):
    policy.init()

    app_hooks = [hooks.ConfigHook(),
                 hooks.DBHook(),
                 hooks.ContextHook(pecan_config.app.acl_public_routes),
                 hooks.RPCHook(),
                 hooks.NoExceptionTracebackHook()]
    if extra_hooks:
        app_hooks.extend(extra_hooks)

    if not pecan_config:
        pecan_config = get_pecan_config()

    pecan.configuration.set_config(dict(pecan_config), overwrite=True)

    app = pecan.make_app(
        pecan_config.app.root,
        static_root=pecan_config.app.static_root,
        debug=CONF.debug,
        force_canonical=getattr(pecan_config.app, 'force_canonical', True),
        hooks=app_hooks,
        wrap_app=middleware.ParsableErrorMiddleware,
    )

    if pecan_config.app.enable_acl:
        return acl.install(app, cfg.CONF, pecan_config.app.acl_public_routes)

    return app


class VersionSelectorApplication(object):
    def __init__(self):
        pc = get_pecan_config()
        pc.app.enable_acl = (CONF.auth_strategy == 'keystone')
        self.v1 = setup_app(pecan_config=pc)

    def __call__(self, environ, start_response):
        return self.v1(environ, start_response)
