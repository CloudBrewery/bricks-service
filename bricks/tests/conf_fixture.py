import fixtures
from oslo.config import cfg

from bricks.common import config

CONF = cfg.CONF
CONF.import_opt('use_ipv6', 'bricks.netconf')
CONF.import_opt('host', 'bricks.common.service')


class ConfFixture(fixtures.Fixture):
    """Fixture to manage global conf settings."""

    def __init__(self, conf):
        self.conf = conf

    def setUp(self):
        super(ConfFixture, self).setUp()

        self.conf.set_default('host', 'bwaaaaaaah')
        self.conf.set_default('rpc_backend',
                              'bricks.openstack.common.rpc.impl_fake')
        self.conf.set_default('rpc_cast_timeout', 5)
        self.conf.set_default('rpc_response_timeout', 5)
        self.conf.set_default('connection', "sqlite://", group='database')
        self.conf.set_default('sqlite_synchronous', False)
        self.conf.set_default('use_ipv6', True)
        self.conf.set_default('verbose', True)
        config.parse_args([], default_config_files=[])
        self.addCleanup(self.conf.reset)
