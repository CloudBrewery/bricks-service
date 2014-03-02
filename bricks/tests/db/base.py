"""Bricks DB test base class."""

from bricks.openstack.common import context as bricks_context
from bricks.tests import base


class DbTestCase(base.TestCase):

    def setUp(self):
        super(DbTestCase, self).setUp()
        self.context = bricks_context.get_admin_context()
