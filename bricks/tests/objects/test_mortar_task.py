import mock

from bricks.common import utils as bricks_utils
from bricks.db import api as db_api
from bricks.db.sqlalchemy import models
from bricks import objects

from bricks.tests.db import base
from bricks.tests.db import utils


class TestMortarTaskObject(base.DbTestCase):
    def test_setters(self):
        foo = objects.MortarTask()
        foo.instance_id = 'asdf-1234'
        foo.raw_command = """
ls
        """
        foo.configuration = {'bar': 'baz'}

        bar = foo.as_dict()

        self.assertEqual(bar['instance_id'], foo.instance_id)
        self.assertEqual(bar['raw_command'], foo.raw_command)
        self.assertEqual(bar['configuration']['bar'], 'baz')
