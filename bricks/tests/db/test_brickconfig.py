"""Tests for manipulating Bricks objects via the DB API"""

import six

from bricks.common import exception
from bricks.common import utils as bricks_utils
from bricks.db import api as dbapi

from bricks.tests.db import base
from bricks.tests.db import utils


class DbBrickConfigTestCase(base.DbTestCase):

    def setUp(self):
        super(DbBrickConfigTestCase, self).setUp()
        self.dbapi = dbapi.get_instance()

    def _create_test_brick(self, **kwargs):
        ch = utils.get_test_brick(**kwargs)
        self.dbapi.create_brick(ch)
        return ch

    def _create_test_brickconfig(self, **kwargs):
        node = utils.get_test_brickconfig(**kwargs)
        return self.dbapi.create_brickconfig(node)

    def test_get_brickconfig_list(self):
        uuids = []
        for i in range(1, 6):
            n = utils.get_test_brickconfig(id=i,
                                           uuid=bricks_utils.generate_uuid())
            self.dbapi.create_brickconfig(n)
            uuids.append(six.text_type(n['uuid']))
        res = self.dbapi.get_brickconfig_list()
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_brickconfig_by_id(self):
        bc = self._create_test_brickconfig()
        brickconfig = self.dbapi.get_brickconfig(bc['id'])

        self.assertEqual(brickconfig.uuid, bc['uuid'])

    def test_get_brickconfig_by_uuid(self):
        bc = self._create_test_brickconfig()
        brickconfig = self.dbapi.get_brickconfig(bc['uuid'])

        self.assertEqual(brickconfig.id, bc['id'])

    def test_get_brick_that_does_not_exist(self):
        self.assertRaises(exception.BrickConfigNotFound,
                          self.dbapi.get_brickconfig, 1337)

    def test_update_brickconfig(self):
        bc = self._create_test_brickconfig()
        new_uuid = bricks_utils.generate_uuid()

        bc['uuid'] = new_uuid
        res = self.dbapi.update_brickconfig(bc['id'], {'uuid': new_uuid})

        self.assertEqual(res.uuid, new_uuid)

    def test_update_brickconfig_that_does_not_exist(self):
        new_uuid = bricks_utils.generate_uuid()

        self.assertRaises(exception.BrickConfigNotFound,
                          self.dbapi.update_brickconfig, 1337,
                          {'uuid': new_uuid})

    def test_destroy_brick(self):
        bc = self._create_test_brickconfig()
        self.dbapi.destroy_brickconfig(bc['id'])

        self.assertRaises(exception.BrickConfigNotFound,
                          self.dbapi.get_brickconfig, bc['id'])

    def test_destroy_brickconfig_that_does_not_exist(self):
        self.assertRaises(exception.BrickConfigNotFound,
                          self.dbapi.destroy_brickconfig, 1337)
