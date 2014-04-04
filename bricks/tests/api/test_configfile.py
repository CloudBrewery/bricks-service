"""
Tests for the API /configfiles/ methods.
"""

import datetime

import mock
from oslo.config import cfg

from bricks.common import utils
from bricks.openstack.common import timeutils
from bricks.tests.api import base
from bricks.tests.api import utils as apiutils
from bricks.tests.db import utils as dbutils


class TestListConfigFiles(base.FunctionalTest):

    def test_empty(self):
        data = self.get_json('/configfiles?brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual([], data['configfiles'])

    def test_one(self):
        ndict = dbutils.get_test_configfile()
        config = self.dbapi.create_configfile(ndict)
        data = self.get_json('/configfiles?brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual(config['uuid'], data['configfiles'][0]["uuid"])
        self.assertNotIn('environ', data['configfiles'][0])

    def test_detail(self):
        cdict = dbutils.get_test_configfile()
        config = self.dbapi.create_configfile(cdict)
        data = self.get_json('/configfiles/detail?brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual(config['uuid'], data['configfiles'][0]["uuid"])
        self.assertIn('description', data['configfiles'][0])

    def test_detail_against_single(self):
        cdict = dbutils.get_test_configfile()
        config = self.dbapi.create_configfile(cdict)
        response = self.get_json('/configfiles/%s/detail' % config['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        cf_list = []
        for id in range(5):
            ndict = dbutils.get_test_configfile(
                id=id, uuid=utils.generate_uuid())

            cf = self.dbapi.create_configfile(ndict)
            cf_list.append(cf['uuid'])

        data = self.get_json('/configfiles?brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual(len(data['configfiles']), len(cf_list))
        uuids = [n['uuid'] for n in data['configfiles']]
        self.assertEqual(uuids.sort(), cf_list.sort())

    def test_brickconfig_filter(self):
        cf_list = []
        brickconfig_uuid = utils.generate_uuid()
        for id in range(5):
            ndict = dbutils.get_test_configfile(
                id=id, uuid=utils.generate_uuid(),
                brickconfig_uuid=brickconfig_uuid)

            cf = self.dbapi.create_configfile(ndict)
            cf_list.append(cf['uuid'])

        data = self.get_json(
            '/configfiles?brickconfig_uuid=%s' % brickconfig_uuid)

        self.assertEqual(len(data['configfiles']), len(cf_list))
        uuids = [n['uuid'] for n in data['configfiles']]
        self.assertEqual(uuids.sort(), cf_list.sort())

    def test_links(self):
        uuid = utils.generate_uuid()
        cdict = dbutils.get_test_configfile(id=1, uuid=uuid)
        self.dbapi.create_configfile(cdict)
        data = self.get_json('/configfiles/%s' % uuid)

        self.assertIn('links', data.keys())
        self.assertEqual(2, len(data['links']))
        self.assertIn(uuid, data['links'][0]['href'])
        self.assertTrue(self.validate_link(data['links'][0]['href']))
        self.assertTrue(self.validate_link(data['links'][1]['href']))

    def test_collection_links(self):
        configs = []
        for id in range(5):
            ndict = dbutils.get_test_configfile(
                id=id, uuid=utils.generate_uuid())

            cf = self.dbapi.create_configfile(ndict)
            configs.append(cf['uuid'])
        data = self.get_json('/configfiles?limit=3&brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual(3, len(data['configfiles']))

        next_marker = data['configfiles'][-1]['uuid']
        self.assertIn(next_marker, data['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        configs = []
        for id in range(5):
            ndict = dbutils.get_test_configfile(
                id=id, uuid=utils.generate_uuid())

            cf = self.dbapi.create_configfile(ndict)
            configs.append(cf['uuid'])
        data = self.get_json('/configfiles?brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual(3, len(data['configfiles']))

        next_marker = data['configfiles'][-1]['uuid']
        self.assertIn(next_marker, data['next'])


class TestPatch(base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        cdict = dbutils.get_test_configfile()
        self.dbapi.create_configfile(cdict)

    def test_update_not_found(self):
        uuid = utils.generate_uuid()
        response = self.patch_json('/configfiles/%s' % uuid,
                                   [{'path': '/contents',
                                     'value': 'RUN: ls -lash',
                                     'op': 'replace'}],
                                   expect_errors=True,
                                   context=self.context)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(timeutils, 'utcnow')
    def test_replace_singular(self, mock_utcnow):
        cdict = dbutils.get_test_configfile()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)

        desc = 'foo'
        mock_utcnow.return_value = test_time
        response = self.patch_json('/configfiles/%s' % cdict['uuid'],
                                   [{'path': '/description',
                                     'value': desc, 'op': 'replace'}],
                                   context=self.context)

        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/configfiles/%s' % cdict['uuid'])
        self.assertEqual(desc, result['description'])
        return_updated_at = timeutils.parse_isotime(
            result['updated_at']).replace(tzinfo=None)

        self.assertEqual(test_time, return_updated_at)

    def test_remove_uuid(self):
        cdict = dbutils.get_test_configfile()
        response = self.patch_json('/configfiles/%s' % cdict['uuid'],
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(base.FunctionalTest):

    @mock.patch.object(timeutils, 'utcnow')
    def test_create_configfile(self, mock_utcnow):
        cdict = dbutils.get_test_configfile()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        response = self.post_json(
            '/configfiles', cdict, context=self.context)
        self.assertEqual(201, response.status_int)

        result = self.get_json('/configfiles/%s' % cdict['uuid'])
        self.assertEqual(cdict['uuid'], result['uuid'])
        self.assertFalse(result['updated_at'])
        return_created_at = timeutils.parse_isotime(result['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_configfile_generate_uuid(self):
        cdict = dbutils.get_test_configfile()
        del cdict['uuid']
        self.post_json('/configfiles', cdict, context=self.context)
        result = self.get_json('/configfiles?brickconfig_uuid=1be26c0b-03f2-4d2e-ae87-c02d7f33c123')
        self.assertEqual(cdict['name'],
                         result['configfiles'][0]['name'])
        self.assertTrue(utils.is_uuid_like(result['configfiles'][0]['uuid']))

    def test_create_configfile_invalid_name(self):
        cdict = dbutils.get_test_configfile()
        del cdict['name']
        response = self.post_json('/configfiles', cdict,
                                  expect_errors=True, context=self.context)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestDelete(base.FunctionalTest):

    def test_delete_configfile(self):
        cdict = dbutils.get_test_configfile()
        self.dbapi.create_configfile(cdict)
        self.delete('/configfiles/%s' % cdict['uuid'], context=self.context)
        response = self.get_json('/configfiles/%s' % cdict['uuid'],
                                 expect_errors=True, context=self.context)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_brick_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/configfiles/%s' % uuid,
                               expect_errors=True, context=self.context)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
