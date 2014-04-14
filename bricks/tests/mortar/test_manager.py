import time

import mock
from oslo.config import cfg

from bricks.mortar import manager
from bricks.openstack.common import context
from bricks.tests.db import base
from bricks import objects


CONF = cfg.CONF


class ManagerTestCase(base.DbTestCase):

    def setUp(self):
        super(ManagerTestCase, self).setUp()
        self.service = manager.MortarManager('test-host', 'test-topic')
        self.context = context.get_admin_context()

    def test_do_execute_simple(self):
        self.assertEqual(True, True)

    @mock.patch('bricks.mortar.utils.do_tail_brick_log')
    def test_tail_log(self, do_tail_fn):
        def tailer(ctx, brick_log):
            brick_log.log = "asdf1234"
            return brick_log
        do_tail_fn.side_effect = tailer

        self.service.start()
        bl = objects.BrickLog()
        bl.uuid = 'x'
        bl.instance_id = 'y'
        bl.length = 10
        sut_bl = self.service.do_tail_brick_log(self.context, bl)

        self.assertEqual(sut_bl.log, "asdf1234")
        self.assertEqual(sut_bl.uuid, bl.uuid)
        self.assertEqual(sut_bl.instance_id, bl.instance_id)
        self.assertEqual(sut_bl.length, bl.length)

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
