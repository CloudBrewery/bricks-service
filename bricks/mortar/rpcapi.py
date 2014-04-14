"""
Client side of the conductor RPC API.
"""

from oslo.config import cfg

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

        topic = topic if topic else 'bricks.mortar_manager'

        super(MortarAPI, self).__init__(
            topic=topic,
            serializer=objects_base.BricksObjectSerializer(),
            default_version=self.RPC_API_VERSION)

    def do_ping(self, context, topic=None):
        self.cast(context,
                  self.make_msg('process_notification',
                                notification={'event_type': 'ping'}),
                  topic=topic or self.topic)

    def do_execute(self, context, execution_task, topic=None):
        self.cast(context,
                  self.make_msg('do_execute', execution_task=execution_task),
                  topic=topic or self.topic)

    def do_check_instances(self, context, instance_list, topic=None):
        self.cast(context,
                  self.make_msg('do_check_instances',
                                instance_list=instance_list),
                  topic=topic or self.topic)

    def do_check_last_task(self, context, instance_id, topic=None):
        self.cast(context,
                  self.make_msg('do_check_last_task',
                                instance_id=instance_id),
                  topic=topic or self.topic)

    def do_tail_brick_log(self, context, brick_log, topic=None):
        return self.call(
            context,
            self.make_msg('do_tail_brick_log',
                          brick_log=brick_log),
            topic=topic or self.topic)
