"""
Client side of the conductor RPC API.
"""

from oslo.config import cfg

from bricks.mortar import manager
from bricks.objects import base as objects_base
import bricks.openstack.common.rpc.proxy

cfg.CONF.set_default('allowed_rpc_exception_modules',
                     ['bricks.common.exception',
                      'exceptions', ])


class MortarAPI(bricks.openstack.common.rpc.proxy.RpcProxy):
    """The Mortar messaging API

    API version history:

        1.0 - Initial version.
    """

    RPC_API_VERSION = '1.0'

    def __init__(self, topic=None):
        if topic is None:
            topic = manager.MANAGER_TOPIC

        super(MortarAPI, self).__init__(
            topic=topic,
            serializer=objects_base.BricksObjectSerializer(),
            default_version=self.RPC_API_VERSION)

    def do_ping(self, context, topic=None):
        self.cast(context,
                  self.make_msg('process_notification',
                                notification={'event_type': 'ping'}),
                  topic=topic or self.topic)

    def do_execute(self, context, execution_list, topic=None):
        self.cast(context,
                  self.make_msg('do_execute', execution_list=execution_list),
                  topic=topic or self.topic)
