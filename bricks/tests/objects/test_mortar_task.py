from bricks import objects
from bricks.tests.db import base


class TestMortarTaskObject(base.DbTestCase):
    def test_setters(self):
        foo = objects.MortarTask()
        foo.instance_id = 'asdf-1234'
        foo.configuration = {'bar': 'baz'}

        bar = foo.as_dict()

        self.assertEqual(bar['instance_id'], foo.instance_id)
        self.assertEqual(bar['configuration']['bar'], 'baz')
