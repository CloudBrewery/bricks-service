import mock

from bricks.common import utils as bricks_utils
from bricks.db import api as db_api
from bricks.db.sqlalchemy import models
from bricks import objects

from bricks.tests.db import base
from bricks.tests.db import utils


# XXX: Implement more awesome testing.

class TestBrickObject(base.DbTestCase):

    def setUp(self):
        super(TestBrickObject, self).setUp()
        self.fake_brick = utils.get_test_brick()
        self.dbapi = db_api.get_instance()

    def test_load(self):
        uuid = self.fake_brick['uuid']
        with mock.patch.object(self.dbapi, 'get_brick',
                               autospec=True) as mock_get_brick:
            mock_get_brick.return_value = self.fake_brick

            objects.Brick.get_by_uuid(self.context, uuid)

            mock_get_brick.assert_called_once_with(uuid)

    def test_save(self):
        uuid = self.fake_brick['uuid']
        with mock.patch.object(self.dbapi, 'get_brick',
                               autospec=True) as mock_get_brick:
            mock_get_brick.return_value = self.fake_brick
            with mock.patch.object(self.dbapi, 'update_brick',
                                   autospec=True) as mock_update_brick:

                c = objects.Brick.get_by_uuid(self.context, uuid)
                c.configuration = {"test": 123}
                c.save()

                mock_get_brick.assert_called_once_with(uuid)
                mock_update_brick.assert_called_once_with(
                    uuid, {'configuration': {"test": 123}})

    def test_refresh(self):
        uuid = self.fake_brick['uuid']
        new_uuid = bricks_utils.generate_uuid()
        returns = [dict(self.fake_brick, uuid=uuid),
                   dict(self.fake_brick, uuid=new_uuid)]
        expected = [mock.call(uuid), mock.call(uuid)]
        with mock.patch.object(self.dbapi, 'get_brick', side_effect=returns,
                               autospec=True) as mock_get_brick:
            c = objects.Brick.get_by_uuid(self.context, uuid)
            self.assertEqual(c.uuid, uuid)
            c.refresh()
            self.assertEqual(c.uuid, new_uuid)
            self.assertEqual(mock_get_brick.call_args_list, expected)

    def test_objectify(self):
        def _get_db_brick():
            c = models.Brick()
            c.update(self.fake_brick)
            return c

        @objects.objectify(objects.Brick)
        def _convert_db_brick():
            return _get_db_brick()

        self.assertIsInstance(_get_db_brick(), models.Brick)
        self.assertIsInstance(_convert_db_brick(), objects.Brick)

    def test_objectify_many(self):
        def _get_many_db_brick():
            bricks = []
            for i in range(5):
                c = models.Brick()
                c.update(self.fake_brick)
                bricks.append(c)
            return bricks

        @objects.objectify(objects.Brick)
        def _convert_many_brick():
            return _get_many_db_brick()

        for c in _get_many_db_brick():
            self.assertIsInstance(c, models.Brick)
        for c in _convert_many_brick():
            self.assertIsInstance(c, objects.Brick)
