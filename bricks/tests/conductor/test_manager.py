import time

import mock
from oslo.config import cfg

from bricks.conductor import manager
from bricks.db import api as dbapi
from bricks.openstack.common import context
from bricks.tests.db import base
from bricks.tests.db import utils

CONF = cfg.CONF


class ManagerTestCase(base.DbTestCase):

    def setUp(self):
        super(ManagerTestCase, self).setUp()
        self.service = manager.ConductorManager('test-host', 'test-topic')
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()

    def test_brick_destroy_simple(self):
        pass

    def test_notify_completion_simple(self):
        pass

    def test_assign_floating_ip_simple(self):
        pass

    def test_brick_deploy_simple(self):
        brickconfig_dict = utils.get_test_brickconfig()
        brickconfig = self.dbapi.create_brickconfig(brickconfig_dict)

        brick_dict = utils.get_test_brick(instance_id=None)
        brick = self.dbapi.create_brick(brick_dict)

        self.service.start()

        with mock.patch('bricks.conductor.utils.deploy_nova_server') \
                as deploy:
            deploy.return_value = "asdf-1234"
            self.service.do_brick_deploy(self.context, brick['uuid'])
            brick.refresh(self.context)
            self.assertEqual(brick['instance_id'], 'asdf-123')
            deploy.assert_called_once_with(mock.ANY, mock.ANY)

    def test__spawn_worker(self):
        func_mock = mock.Mock()
        args = (1, 2, "test")
        kwargs = dict(kw1='test1', kw2='test2')
        self.service.start()

        thread = self.service._spawn_worker(func_mock, *args, **kwargs)
        self.service._worker_pool.waitall()

        self.assertIsNotNone(thread)
        func_mock.assert_called_once_with(*args, **kwargs)

    # The tests below related to greenthread. We have they to assert our
    # assumptions about greenthread behavior.

    def test__spawn_link_callback_added_during_execution(self):
        def func():
            time.sleep(1)
        link_callback = mock.Mock()
        self.service.start()

        thread = self.service._spawn_worker(func)
        # func_mock executing at this moment
        thread.link(link_callback)
        self.service._worker_pool.waitall()

        link_callback.assert_called_once_with(thread)

    def test__spawn_link_callback_added_after_execution(self):
        def func():
            pass
        link_callback = mock.Mock()
        self.service.start()

        thread = self.service._spawn_worker(func)
        self.service._worker_pool.waitall()
        # func_mock finished at this moment
        thread.link(link_callback)

        link_callback.assert_called_once_with(thread)

    def test__spawn_link_callback_exception_inside_thread(self):
        def func():
            time.sleep(1)
            raise Exception()
        link_callback = mock.Mock()
        self.service.start()

        thread = self.service._spawn_worker(func)
        # func_mock executing at this moment
        thread.link(link_callback)
        self.service._worker_pool.waitall()

        link_callback.assert_called_once_with(thread)

    def test__spawn_link_callback_added_after_exception_inside_thread(self):
        def func():
            raise Exception()
        link_callback = mock.Mock()
        self.service.start()

        thread = self.service._spawn_worker(func)
        self.service._worker_pool.waitall()
        # func_mock finished at this moment
        thread.link(link_callback)

        link_callback.assert_called_once_with(thread)
