
# vim: tabstop=4 shiftwidth=4 softtabstop=4
# -*- encoding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Tests for the API /brickconfigs/ methods.
"""

import datetime

import mock
from oslo.config import cfg

from bricks.common import utils
from bricks.openstack.common import timeutils
from bricks.tests.api import base
from bricks.tests.api import utils as apiutils
from bricks.tests.db import utils as dbutils


class TestListBrickConfigs(base.FunctionalTest):

    def test_empty(self):
        data = self.get_json('/brickconfigs')
        self.assertEqual([], data['brickconfigs'])

    def test_one(self):
        ndict = dbutils.get_test_brickconfig()
        brick = self.dbapi.create_brickconfig(ndict)
        data = self.get_json('/brickconfigs')
        self.assertEqual(brick['uuid'], data['brickconfigs'][0]["uuid"])
        self.assertNotIn('environ', data['brickconfigs'][0])

    def test_not_public(self):

        self.context.tenant = 'justauser'
        self.context.is_admin = False

        ndict = dbutils.get_test_brickconfig(is_public=False,
                                             tenant_id=self.context.tenant)
        brick = self.dbapi.create_brickconfig(ndict)
        # user can get their own.
        data = self.get_json(
            '/brickconfigs?is_public=False&tenant_id=%s' %
            self.context.tenant, context=self.context)
        self.assertEqual(brick['uuid'], data['brickconfigs'][0]['uuid'])

        # unauthenticated list, there are no public ones
        nodata = self.get_json('/brickconfigs')
        self.assertEqual(0, len(nodata['brickconfigs']))

        # unauthenticated listof is_public without announcing your own tenant
        faildata = self.get_json(
            '/brickconfigs?is_public=False',
            expect_errors=True,
            context=self.context)
        self.assertEqual(403, faildata.status_int)

        # admin can list them though.
        self.context.tenant = None
        self.context.is_admin = True

        admindata = self.get_json(
            '/brickconfigs?is_public=False&tenant_id=justauser',
            context=self.context)
        self.assertEqual(1, len(admindata['brickconfigs']))

    def test_detail(self):
        cdict = dbutils.get_test_brickconfig()
        brick = self.dbapi.create_brickconfig(cdict)
        data = self.get_json('/brickconfigs/detail')
        self.assertEqual(brick['uuid'], data['brickconfigs'][0]["uuid"])
        self.assertIn('environ', data['brickconfigs'][0])

    def test_detail_against_single(self):
        cdict = dbutils.get_test_brick()
        brick = self.dbapi.create_brickconfig(cdict)
        response = self.get_json('/brickconfigs/%s/detail' % brick['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        br_list = []
        for id in range(5):
            ndict = dbutils.get_test_brickconfig(id=id, uuid=utils.generate_uuid())
            brick = self.dbapi.create_brickconfig(ndict)
            br_list.append(brick['uuid'])
        data = self.get_json('/brickconfigs')
        self.assertEqual(len(data['brickconfigs']), len(br_list))
        uuids = [n['uuid'] for n in data['brickconfigs']]
        self.assertEqual(uuids.sort(), br_list.sort())

    def test_links(self):
        uuid = utils.generate_uuid()
        ndict = dbutils.get_test_brick(id=1, uuid=uuid)
        self.dbapi.create_brickconfig(ndict)
        data = self.get_json('/brickconfigs/%s' % uuid)
        self.assertIn('links', data.keys())
        self.assertEqual(2, len(data['links']))
        self.assertIn(uuid, data['links'][0]['href'])
        self.assertTrue(self.validate_link(data['links'][0]['href']))
        self.assertTrue(self.validate_link(data['links'][1]['href']))

    def test_collection_links(self):
        bricks = []
        for id in range(5):
            ndict = dbutils.get_test_brickconfig(id=id, uuid=utils.generate_uuid())
            br = self.dbapi.create_brickconfig(ndict)
            bricks.append(br['uuid'])
        data = self.get_json('/brickconfigs/?limit=3')
        self.assertEqual(3, len(data['brickconfigs']))

        next_marker = data['brickconfigs'][-1]['uuid']
        self.assertIn(next_marker, data['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        bricks = []
        for id in range(5):
            ndict = dbutils.get_test_brickconfig(id=id, uuid=utils.generate_uuid())
            br = self.dbapi.create_brickconfig(ndict)
            bricks.append(br['uuid'])
        data = self.get_json('/brickconfigs')
        self.assertEqual(3, len(data['brickconfigs']))

        next_marker = data['brickconfigs'][-1]['uuid']
        self.assertIn(next_marker, data['next'])


class TestPatch(base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        cdict = dbutils.get_test_brickconfig()
        self.dbapi.create_brickconfig(cdict)

    def test_update_not_found(self):
        uuid = utils.generate_uuid()
        response = self.patch_json('/brickconfigs/%s' % uuid,
                                   [{'path': '/environ/a',
                                     'value': 'b',
                                     'op': 'add'}],
                                   expect_errors=True,
                                   context=self.context)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(timeutils, 'utcnow')
    def test_replace_singular(self, mock_utcnow):
        cdict = dbutils.get_test_brickconfig()
        version = 'deploying'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)

        mock_utcnow.return_value = test_time
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/version',
                                     'value': version, 'op': 'replace'}],
                                   context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])
        self.assertEqual(version, result['version'])
        return_updated_at = timeutils.parse_isotime(
            result['updated_at']).replace(tzinfo=None)

        self.assertEqual(test_time, return_updated_at)

    def test_replace_multi(self):
        environ = {"foo1": "bar1", "foo2": "bar2", "foo3": "bar3"}
        cdict = dbutils.get_test_brickconfig(
            environ=environ, uuid=utils.generate_uuid(), id=None)
        self.dbapi.create_brickconfig(cdict)
        new_value = 'new value'
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/environ/foo2',
                                     'value': new_value, 'op': 'replace'}],
                                   context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])

        environ["foo2"] = new_value
        self.assertEqual(environ, result['environ'])

    def test_remove_singular(self):
        cdict = dbutils.get_test_brickconfig(environ={'a': 'b'},
                                       uuid=utils.generate_uuid(),
                                       id=None)
        self.dbapi.create_brickconfig(cdict)
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/environ/a', 'op': 'remove'}],
                                   context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])

        # Assert nothing else was changed
        self.assertEqual(cdict['uuid'], result['uuid'])
        self.assertNotEqual(cdict['environ'], result['environ'])

    def test_remove_multi(self):
        environ = {"foo1": "bar1", "foo2": "bar2", "foo3": "bar3"}
        cdict = dbutils.get_test_brickconfig(
            environ=environ, status="in progress",
            uuid=utils.generate_uuid(), id=None)
        self.dbapi.create_brickconfig(cdict)

        # Removing one item from the collection
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/environ/foo2', 'op': 'remove'}],
                                   context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])
        environ.pop("foo2")
        self.assertEqual(environ, result['environ'])

        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])
        self.assertEqual(environ, result['environ'])

        # Assert nothing else was changed
        self.assertEqual(cdict['uuid'], result['uuid'])

    def test_remove_non_existent_property_fail(self):
        cdict = dbutils.get_test_brickconfig()
        response = self.patch_json(
            '/brickconfigs/%s' % cdict['uuid'],
            [{'path': '/environ/non-existent', 'op': 'remove'}],
            expect_errors=True, context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_add_singular(self):
        cdict = dbutils.get_test_brickconfig()
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/foo', 'value': 'bar',
                                     'op': 'add'}],
                                   expect_errors=True,
                                   context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_add_multi(self):
        cdict = apiutils.get_test_brick_json()
        cdict = dbutils.get_test_brickconfig()
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/environ/foo1', 'value': 'bar1',
                                     'op': 'add'},
                                    {'path': '/environ/foo2', 'value': 'bar2',
                                     'op': 'add'}],
                                   context=self.context)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])
        expected = {"foo1": "bar1", "foo2": "bar2"}
        self.assertEqual(expected, result['environ'])

    def test_remove_uuid(self):
        cdict = apiutils.get_test_brick_json()
        cdict = dbutils.get_test_brickconfig()
        response = self.patch_json('/brickconfigs/%s' % cdict['uuid'],
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(base.FunctionalTest):

    @mock.patch.object(timeutils, 'utcnow')
    def test_create_brickconfig(self, mock_utcnow):
        cdict = dbutils.get_test_brickconfig()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        response = self.post_json('/brickconfigs', cdict, context=self.context)
        self.assertEqual(201, response.status_int)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])
        self.assertEqual(cdict['uuid'], result['uuid'])
        self.assertFalse(result['updated_at'])
        return_created_at = timeutils.parse_isotime(result['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_brickconfig_generate_uuid(self):
        cdict = dbutils.get_test_brickconfig()
        del cdict['uuid']
        self.post_json('/brickconfigs', cdict, context=self.context)
        result = self.get_json('/brickconfigs')
        self.assertEqual(cdict['version'],
                         result['brickconfigs'][0]['version'])
        self.assertTrue(utils.is_uuid_like(result['brickconfigs'][0]['uuid']))

    def test_create_brickconfig_valid_environ(self):
        cdict = dbutils.get_test_brickconfig(environ={'foo': 'bar'})
        self.post_json('/brickconfigs', cdict, context=self.context)
        result = self.get_json('/brickconfigs/%s' % cdict['uuid'])
        self.assertEqual(cdict['environ'], result['environ'])

    def test_create_brickconfig_invalid_environ(self):
        cdict = dbutils.get_test_brickconfig(environ={'foo': 123})
        response = self.post_json('/brickconfigs', cdict,
                                  expect_errors=True, context=self.context)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestDelete(base.FunctionalTest):

    def test_delete_brickconfig(self):
        cdict = dbutils.get_test_brickconfig()
        self.dbapi.create_brickconfig(cdict)
        self.delete('/brickconfigs/%s' % cdict['uuid'], context=self.context)
        response = self.get_json('/brickconfigs/%s' % cdict['uuid'],
                                 expect_errors=True, context=self.context)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_brick_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/brickconfigs/%s' % uuid,
                               expect_errors=True, context=self.context)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
