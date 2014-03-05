import mock

from bricks.common import states
from bricks.conductor import utils as conductor_utils
from bricks.db import api as dbapi
from bricks.openstack.common import context
from bricks.tests.conductor import utils as mgr_utils
from bricks.tests.db import base


class DeployTestCase(base.DbTestCase):

    def setUp(self):
        super(DeployTestCase, self).setUp()
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
