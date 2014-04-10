from bricks.mortar import utils
from bricks.objects import mortar_task
from bricks.openstack.common import context
from bricks.tests.db import base


class ExecuteTaskTestCase(base.DbTestCase):

    def setUp(self):
        super(ExecuteTaskTestCase, self).setUp()
        self.context = context.get_admin_context()

    def x_test_task_execute_full(self):
        # XXX: TEST ME
        test_task = mortar_task.MortarTask()
        test_task.instance_id = "test123"
        test_task.configuration = {'Dockerfile': """
RUN: ls
"""}
        fake_execution_list = test_task

        results = utils.do_execute(self.context, fake_execution_list)
        print results
