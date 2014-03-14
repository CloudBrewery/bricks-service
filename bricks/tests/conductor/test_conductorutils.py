from bricks.db import api as dbapi
from bricks.openstack.common import context
from bricks.tests.db import base


class DeployTestCase(base.DbTestCase):

    def setUp(self):
        super(DeployTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class InitTestCase(base.DbTestCase):

    def setUp(self):
        super(InitTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class DestroyTestCase(base.DbTestCase):

    def setUp(self):
        super(DestroyTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()


class IPAssignTestCase(base.DbTestCase):

    def setUp(self):
        super(DestroyTestCase, self).setUp()
        self.context = context.get_admin_context()
        self.dbapi = dbapi.get_instance()
