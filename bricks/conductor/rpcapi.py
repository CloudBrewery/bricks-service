"""
Client side of the conductor RPC API.
"""

from oslo.config import cfg

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
        topic = 'bricks.conductor_manager'

        super(ConductorAPI, self).__init__(
            topic=topic,
            serializer=objects_base.BricksObjectSerializer(),
            default_version=self.RPC_API_VERSION)

    def do_ping(self, context, topic=None):
        self.cast(context,
                  self.make_msg('process_notification', notification={'event_type': 'ping'}),
                  topic=topic or self.topic)

    def do_brick_deploy(self, context, brick_id, topic=None):
        self.cast(context,
                  self.make_msg('do_brick_deploy', brick_id=brick_id),
                  topic=topic or self.topic)

    def do_brick_deploying(self, context, brick_id, topic=None):
        self.cast(context,
                  self.make_msg('do_brick_deploying', brick_id=brick_id),
                  topic=topic or self.topic)

    def do_brick_deployfail(self, context, brick_id, topic=None):
        self.cast(context,
                  self.make_msg('do_brick_deployfail', brick_id=brick_id),
                  topic=topic or self.topic)

    def do_brick_deploydone(self, context, brick_id, topic=None):
        self.cast(context,
                  self.make_msg('do_brick_deploydone', brick_id=brick_id),
                  topic=topic or self.topic)

    def do_brick_destroy(self, context, brick_id, topic=None):
        self.cast(context,
                  self.make_msg('do_brick_destroy', brick_id=brick_id),
                  topic=topic or self.topic)

    def notify_completion(self, context, brick_id, topic=None):
        self.cast(context,
                  self.make_msg('notify_completion', brick_id=brick_id),
                  topic=topic or self.topic)
