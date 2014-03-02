import mock

from bricks.common import utils as bricks_utils
from bricks.db import api as db_api
from bricks.db.sqlalchemy import models
from bricks import objects

from bricks.tests.db import base
from bricks.tests.db import utils


# XXX: Implement more awesome testing.

class TestBrickConfigObject(base.DbTestCase):

    def setUp(self):
        super(TestBrickConfigObject, self).setUp()
        self.fake_brickconfig = utils.get_test_brickconfig()
        self.dbapi = db_api.get_instance()

    def test_load(self):
        uuid = self.fake_brickconfig['uuid']
        with mock.patch.object(self.dbapi, 'get_brickconfig',
                               autospec=True) as mock_get_brickconfig:
            mock_get_brickconfig.return_value = self.fake_brickconfig

            objects.BrickConfig.get_by_uuid(self.context, uuid)

            mock_get_brickconfig.assert_called_once_with(uuid)

    def test_save(self):
        uuid = self.fake_brickconfig['uuid']
        with mock.patch.object(self.dbapi, 'get_brickconfig',
                               autospec=True) as mock_get_brickconfig:
            mock_get_brickconfig.return_value = self.fake_brickconfig
            with mock.patch.object(self.dbapi, 'update_brickconfig',
                                   autospec=True) as mock_update_brickconfig:

                c = objects.BrickConfig.get_by_uuid(self.context, uuid)
                c.ports = [1,2,3]
                c.save()

                mock_get_brickconfig.assert_called_once_with(uuid)
                mock_update_brickconfig.assert_called_once_with(
                    uuid, {'ports': [1,2,3]})

    def test_refresh(self):
        uuid = self.fake_brickconfig['uuid']
        new_uuid = bricks_utils.generate_uuid()
        returns = [dict(self.fake_brickconfig, uuid=uuid),
                   dict(self.fake_brickconfig, uuid=new_uuid)]
        expected = [mock.call(uuid), mock.call(uuid)]
        with mock.patch.object(self.dbapi, 'get_brickconfig', side_effect=returns,
                               autospec=True) as mock_get_brickconfig:
            c = objects.BrickConfig.get_by_uuid(self.context, uuid)
            self.assertEqual(c.uuid, uuid)
            c.refresh()
            self.assertEqual(c.uuid, new_uuid)
            self.assertEqual(mock_get_brickconfig.call_args_list, expected)

    def test_objectify(self):
        def _get_db_brick():
            c = models.Brick()
            c.update(self.fake_brickconfig)
            return c

        @objects.objectify(objects.BrickConfig)
        def _convert_db_brick():
            return _get_db_brick()

        self.assertIsInstance(_get_db_brick(), models.Brick)
        self.assertIsInstance(_convert_db_brick(), objects.BrickConfig)

    def test_objectify_many(self):
        def _get_many_db_brick():
            bricks = []
            for i in range(5):
                c = models.Brick()
                c.update(self.fake_brickconfig)
                bricks.append(c)
            return bricks

        @objects.objectify(objects.BrickConfig)
        def _convert_many_brick():
            return _get_many_db_brick()

        for c in _get_many_db_brick():
            self.assertIsInstance(c, models.Brick)
        for c in _convert_many_brick():
            self.assertIsInstance(c, objects.BrickConfig)
