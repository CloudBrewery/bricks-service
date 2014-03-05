import fixtures

from oslo.config import cfg

from bricks.conductor import rpcapi as conductor_rpcapi
from bricks.db import api as dbapi
from bricks import objects
from bricks.openstack.common import context
from bricks.openstack.common import jsonutils as json
from bricks.tests.db import base
from bricks.tests.db import utils as dbutils

CONF = cfg.CONF


class RPCAPITestCase(base.DbTestCase):

    def setUp(self):
        super(RPCAPITestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()
        self.fake_brick = json.to_primitive(
            dbutils.get_test_brick())
        self.fake_brick_obj = objects.Brick._from_db_object(
            objects.Brick(), self.fake_brick)

    def test_serialized_instance_has_uuid(self):
        self.assertTrue('uuid' in self.fake_brick)

    def test_get_correct_topic(self):
        rpcapi = conductor_rpcapi.ConductorAPI(topic='fake-topic')
        self.assertEqual('fake-topic', rpcapi._get_topic(None))

    def _test_rpcapi(self, method, rpc_method, **kwargs):
        ctxt = context.get_admin_context()
        rpcapi = conductor_rpcapi.ConductorAPI(topic='fake-topic')

        expected_retval = 'hello world' if rpc_method == 'call' else None
        expected_version = kwargs.pop('version', rpcapi.RPC_API_VERSION)
        expected_msg = rpcapi.make_msg(method, **kwargs)

        expected_msg['version'] = expected_version

        expected_topic = 'fake-topic'

        if 'host' in kwargs:
            expected_topic += ".%s" % kwargs['host']

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

    def test_do_brick_deploy(self):
        self._test_rpcapi('do_brick_deploy', 'cast',
                          brick_id=self.fake_brick['uuid'])

    def test_do_brick_destroy(self):
        self._test_rpcapi('do_brick_destroy', 'cast',
                          brick_id=self.fake_brick['uuid'])

    def test_notify_completion(self):
        self._test_rpcapi('notify_completion', 'cast',
                          brick_id=self.fake_brick['uuid'])

    def test_assign_floating_ip(self):
        self._test_rpcapi('assign_floating_ip', 'cast',
                          brick_id=self.fake_brick['uuid'],
                          floating_ip='127.0.0.1')
