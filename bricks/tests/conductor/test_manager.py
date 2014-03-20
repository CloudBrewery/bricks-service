import time

import mock
from oslo.config import cfg

from bricks.common import states
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
        # TODO(thurloat): test brick destroying manager call
        pass

    def test_notify_completion_simple(self):
        # TODO(thurloat): test completion manager call
        pass

    def test_assign_floating_ip_simple(self):
        brickconfig_dict = utils.get_test_brickconfig()
        self.dbapi.create_brickconfig(brickconfig_dict)

        brick_dict = utils.get_test_brick(status='borked')
        brick = self.dbapi.create_brick(brick_dict)

        self.service.start()
        with mock.patch('bricks.conductor.utils._drive_floating_ip') \
                as flop_action:
            flop_action.return_value = None
            self.service.assign_floating_ip(self.context, brick['uuid'],
                                            '127.0.0.1')
            self.service._worker_pool.waitall()
            brick.refresh(self.context)
            self.assertEqual(brick['status'], states.NETWORKED)
            flop_action.assert_called_once_with(mock.ANY, mock.ANY, mock.ANY)

    def test_brick_deploy_simple(self):
        brickconfig_dict = utils.get_test_brickconfig()
        self.dbapi.create_brickconfig(brickconfig_dict)

        brick_dict = utils.get_test_brick(instance_id=None)
        brick = self.dbapi.create_brick(brick_dict)

        self.service.start()

        with mock.patch('bricks.conductor.utils._deploy_nova_server') \
                as deploy:
            deploy.return_value = "asdf-1234"
            self.service.do_brick_deploy(self.context, brick['uuid'])
            self.service._worker_pool.waitall()
            brick.refresh(self.context)
            self.assertEqual(brick['instance_id'], 'asdf-1234')
            deploy.assert_called_once_with(mock.ANY, mock.ANY, mock.ANY)

    def test_brick_deploying(self):
        brick_dict = utils.get_test_brick()
        brick = self.dbapi.create_brick(brick_dict)

        self.service.start()
        self.service.do_brick_deploying(self.context, brick['uuid'])
        self.service._worker_pool.waitall()
        brick.refresh(self.context)
        self.assertEqual(brick['status'], states.DEPLOYING)

    def test_brick_deployfail(self):
        brick_dict = utils.get_test_brick()
        brick = self.dbapi.create_brick(brick_dict)

        self.service.start()
        self.service.do_brick_deployfail(self.context, brick['uuid'])
        self.service._worker_pool.waitall()
        brick.refresh(self.context)
        self.assertEqual(brick['status'], states.DEPLOYFAIL)

    def test_brick_deploydone(self):
        brick_dict = utils.get_test_brick()
        brick = self.dbapi.create_brick(brick_dict)

        self.service.start()
        self.service.do_brick_deploydone(self.context, brick['uuid'])
        self.service._worker_pool.waitall()
        brick.refresh(self.context)
        self.assertEqual(brick['status'], states.DEPLOYDONE)

    def test__spawn_worker(self):
        func_mock = mock.Mock()
        args = (1, 2, "test")
        kwargs = dict(kw1='test1', kw2='test2')
        self.service.start()

        thread = self.service._spawn_worker(func_mock, *args, **kwargs)
        self.service._worker_pool.waitall()

        self.assertIsNotNone(thread)
        func_mock.assert_called_once_with(*args, **kwargs)

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
