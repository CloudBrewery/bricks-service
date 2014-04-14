"""Tests for manipulating Brick objects via the DB API"""

import six

from bricks.common import exception
from bricks.common import utils as bricks_utils
from bricks.db import api as dbapi

from bricks.tests.db import base
from bricks.tests.db import utils


class DbBrickTestCase(base.DbTestCase):

    def setUp(self):
        super(DbBrickTestCase, self).setUp()
        self.dbapi = dbapi.get_instance()

    def _create_test_brick(self, **kwargs):
        ch = utils.get_test_brick(**kwargs)
        self.dbapi.create_brick(ch)
        return ch

    def _create_test_brickconfig(self, **kwargs):
        node = utils.get_test_brickconfig(**kwargs)
        return self.dbapi.create_brickconfig(node)

    def test_get_brick_list(self):
        uuids = []
        for i in range(1, 6):
            n = utils.get_test_brick(id=i, uuid=bricks_utils.generate_uuid())
            self.dbapi.create_brick(n)
            uuids.append(six.text_type(n['uuid']))
        res = self.dbapi.get_brick_list()
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_brick_by_id(self):
        br = self._create_test_brick()
        brick = self.dbapi.get_brick(br['id'])

        self.assertEqual(brick.uuid, br['uuid'])

    def test_get_brick_by_uuid(self):
        br = self._create_test_brick()
        brick = self.dbapi.get_brick(br['uuid'])

        self.assertEqual(brick.id, br['id'])

    def test_get_brick_by_instance_id(self):
        br = self._create_test_brick(instance_id="abc123")
        brick = self.dbapi.get_brick(brick_id=None, instance_id="abc123")
        self.assertEqual(brick.uuid, br['uuid'])

    def test_get_brick_that_does_not_exist(self):
        self.assertRaises(exception.BrickNotFound,
                          self.dbapi.get_brick, 1337)

    def test_update_brick(self):
        br = self._create_test_brick()
        new_uuid = bricks_utils.generate_uuid()

        br['uuid'] = new_uuid
        res = self.dbapi.update_brick(br['id'], {'uuid': new_uuid})

        self.assertEqual(res.uuid, new_uuid)

    def test_update_brick_that_does_not_exist(self):
        new_uuid = bricks_utils.generate_uuid()

        self.assertRaises(exception.BrickNotFound,
                          self.dbapi.update_brick, 1337, {'uuid': new_uuid})

    def test_destroy_brick(self):
        br = self._create_test_brick()
        self.dbapi.destroy_brick(br['id'])

        self.assertRaises(exception.BrickNotFound,
                          self.dbapi.get_brick, br['id'])

        # make sure it doesn't show up in lists as well
        bricks = self.dbapi.get_brick_list()
        self.assertEqual(0, len(bricks))

    def test_destroy_brick_that_does_not_exist(self):
        self.assertRaises(exception.BrickNotFound,
                          self.dbapi.destroy_brick, 1337)
