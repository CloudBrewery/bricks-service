"""
Client side of the conductor RPC API.
"""

from oslo.config import cfg

from bricks.common import exception
from bricks.common import hash_ring as hash
from bricks.conductor import manager
from bricks.db import api as dbapi
from bricks.objects import base as objects_base
import bricks.openstack.common.rpc.proxy

# NOTE(max_lobur): This is temporary override for Oslo setting defined in
# ironic.openstack.common.rpc.__init__.py. Should stay while Oslo is not fixed.
# *The setting shows what exceptions can be deserialized from RPC response.
# *This won't be reflected in ironic.conf.sample
# TODO(max_lobur): cover this by an integration test as
# described in https://bugs.launchpad.net/ironic/+bug/1252824
cfg.CONF.set_default('allowed_rpc_exception_modules',
                     ['bricks.common.exception',
                      'exceptions', ])


class ConductorAPI(bricks.openstack.common.rpc.proxy.RpcProxy):
    """Client side of the conductor RPC API.

    API version history:

        1.0 - Initial version.
    """

    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        if topic is None:
            topic = manager.MANAGER_TOPIC

        # Initialize consistent hash ring
        self.hash_rings = {}
        d2c = dbapi.get_instance().get_active_driver_dict()
        for driver in d2c.keys():
            self.hash_rings[driver] = hash.HashRing(d2c[driver])

        super(ConductorAPI, self).__init__(
            topic=topic,
            serializer=objects_base.BricksObjectSerializer(),
            default_version=self.RPC_API_VERSION)
