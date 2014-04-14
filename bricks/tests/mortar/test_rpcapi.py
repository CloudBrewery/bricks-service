import fixtures

from oslo.config import cfg

from bricks import objects
from bricks.mortar import rpcapi as mortar_rpcapi
from bricks.openstack.common import context
from bricks.tests.db import base

CONF = cfg.CONF


class RPCAPITestCase(base.DbTestCase):

    def setUp(self):
        super(RPCAPITestCase, self).setUp()
        self.context = context.get_admin_context()

    def test_get_correct_topic(self):
        rpcapi = mortar_rpcapi.MortarAPI(topic='fake-topic')
        self.assertEqual('fake-topic', rpcapi._get_topic(None))

    def _test_rpcapi(self, method, rpc_method, **kwargs):
        ctxt = context.get_admin_context()
        rpcapi = mortar_rpcapi.MortarAPI(topic='fake-topic')

        expected_retval = 'hello world' if rpc_method == 'call' else None
        expected_version = kwargs.pop('version', rpcapi.RPC_API_VERSION)
        expected_msg = rpcapi.make_msg(method, **kwargs)

        expected_msg['version'] = expected_version

        expected_topic = 'fake-topic'

        self.fake_args = None
        self.fake_kwargs = None

        def _fake_rpc_method(*args, **kwargs):
            self.fake_args = args
            self.fake_kwargs = kwargs

            if expected_retval:
                return expected_retval

        self.useFixture(fixtures.MonkeyPatch(
            "bricks.openstack.common.rpc.%s" % rpc_method,
            _fake_rpc_method))

        retval = getattr(rpcapi, method)(ctxt, **kwargs)

        self.assertEqual(retval, expected_retval)
        expected_args = [ctxt, expected_topic, expected_msg]
        for arg, expected_arg in zip(self.fake_args, expected_args):
            self.assertEqual(arg, expected_arg)

    def test_do_execute(self):
        self._test_rpcapi(
            'do_execute', 'cast',
            execution_task=objects.MortarTask().obj_to_primitive())

    def test_tail_log(self):
        bricklog = objects.BrickLog()
        bricklog.uuid = 'x'
        bricklog.instance_id = 'y'
        bricklog.length = 10

        self._test_rpcapi(
            'do_tail_brick_log', 'call',
            brick_log=bricklog.obj_to_primitive())
