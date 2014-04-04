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
Tests for the API /bricks/ methods.
"""

import datetime

import mock
from oslo.config import cfg

from bricks.common import exception
from bricks.common import utils
from bricks.common import states
from bricks.openstack.common import timeutils
from bricks.tests.api import base
from bricks.tests.api import utils as apiutils
from bricks.tests.db import utils as dbutils


class TestListBricks(base.FunctionalTest):

    def test_empty(self):
        data = self.get_json('/bricks')
        self.assertEqual([], data['bricks'])

    def test_one(self):
        ndict = dbutils.get_test_brick()
        brick = self.dbapi.create_brick(ndict)
        data = self.get_json('/bricks')
        self.assertEqual(brick['uuid'], data['bricks'][0]["uuid"])
        self.assertNotIn('configuration', data['bricks'][0])

    def test_detail(self):
        cdict = dbutils.get_test_brick()
        brick = self.dbapi.create_brick(cdict)
        data = self.get_json('/bricks/detail')
        self.assertEqual(brick['uuid'], data['bricks'][0]["uuid"])
        self.assertIn('configuration', data['bricks'][0])

    def test_detail_against_single(self):
        cdict = dbutils.get_test_brick()
        brick = self.dbapi.create_brick(cdict)
        response = self.get_json('/bricks/%s/detail' % brick['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        br_list = []
        for id in range(5):
            ndict = dbutils.get_test_brick(id=id, uuid=utils.generate_uuid())
            brick = self.dbapi.create_brick(ndict)
            br_list.append(brick['uuid'])
        data = self.get_json('/bricks')
        self.assertEqual(len(data['bricks']), len(br_list))
        uuids = [n['uuid'] for n in data['bricks']]
        self.assertEqual(uuids.sort(), br_list.sort())

    def test_links(self):
        uuid = utils.generate_uuid()
        ndict = dbutils.get_test_brick(id=1, uuid=uuid)
        self.dbapi.create_brick(ndict)
        data = self.get_json('/bricks/%s' % uuid)
        self.assertIn('links', data.keys())
        self.assertEqual(2, len(data['links']))
        self.assertIn(uuid, data['links'][0]['href'])
        self.assertTrue(self.validate_link(data['links'][0]['href']))
        self.assertTrue(self.validate_link(data['links'][1]['href']))

    def test_collection_links(self):
        bricks = []
        for id in range(5):
            ndict = dbutils.get_test_brick(id=id, uuid=utils.generate_uuid())
            br = self.dbapi.create_brick(ndict)
            bricks.append(br['uuid'])
        data = self.get_json('/bricks/?limit=3')
        self.assertEqual(3, len(data['bricks']))

        next_marker = data['bricks'][-1]['uuid']
        self.assertIn(next_marker, data['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        bricks = []
        for id in range(5):
            ndict = dbutils.get_test_brick(id=id, uuid=utils.generate_uuid())
            br = self.dbapi.create_brick(ndict)
            bricks.append(br['uuid'])
        data = self.get_json('/bricks')
        self.assertEqual(3, len(data['bricks']))

        next_marker = data['bricks'][-1]['uuid']
        self.assertIn(next_marker, data['next'])


class TestPatch(base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        cdict = dbutils.get_test_brick()
        self.dbapi.create_brick(cdict)

    def test_update_not_found(self):
        uuid = utils.generate_uuid()
        response = self.patch_json('/bricks/%s' % uuid,
                                   [{'path': '/configuration/a',
                                     'value': 'b',
                                     'op': 'add'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(timeutils, 'utcnow')
    def test_replace_singular(self, mock_utcnow):
        cdict = apiutils.get_test_brick_json()
        status = 'deploying'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)

        mock_utcnow.return_value = test_time
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/status',
                                     'value': status, 'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/bricks/%s' % cdict['uuid'])
        self.assertEqual(status, result['status'])
        return_updated_at = timeutils.parse_isotime(
            result['updated_at']).replace(tzinfo=None)

        self.assertEqual(test_time, return_updated_at)

    def test_replace_multi(self):
        configuration = {"foo1": "bar1", "foo2": "bar2", "foo3": "bar3"}
        cdict = dbutils.get_test_brick(
            configuration=configuration, uuid=utils.generate_uuid(), id=None)
        self.dbapi.create_brick(cdict)
        new_value = 'new value'
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/configuration/foo2',
                                     'value': new_value, 'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/bricks/%s' % cdict['uuid'])

        configuration["foo2"] = new_value
        self.assertEqual(configuration, result['configuration'])

    def test_remove_singular(self):
        cdict = dbutils.get_test_brick(configuration={'a': 'b'},
                                       uuid=utils.generate_uuid(),
                                       id=None)
        self.dbapi.create_brick(cdict)
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/configuration/a', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/bricks/%s' % cdict['uuid'])

        # Assert nothing else was changed
        self.assertEqual(cdict['uuid'], result['uuid'])
        self.assertNotEqual(cdict['configuration'], result['configuration'])

    def test_remove_multi(self):
        configuration = {"foo1": "bar1", "foo2": "bar2", "foo3": "bar3"}
        cdict = dbutils.get_test_brick(
            configuration=configuration, status="in progress",
            uuid=utils.generate_uuid(), id=None)
        self.dbapi.create_brick(cdict)

        # Removing one item from the collection
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/configuration/foo2', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/bricks/%s' % cdict['uuid'])
        configuration.pop("foo2")
        self.assertEqual(configuration, result['configuration'])

        # Removing the configuration (cannot, mandatory)
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/configuration', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        result = self.get_json('/bricks/%s' % cdict['uuid'])
        self.assertEqual(configuration, result['configuration'])

        # Assert nothing else was changed
        self.assertEqual(cdict['uuid'], result['uuid'])

    def test_remove_non_existent_property_fail(self):
        cdict = apiutils.get_test_brick_json()
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                             [{'path': '/configuration/non-existent', 'op': 'remove'}],
                             expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

    def test_add_singular(self):
        cdict = apiutils.get_test_brick_json()
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/foo', 'value': 'bar',
                                     'op': 'add'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_add_multi(self):
        cdict = apiutils.get_test_brick_json()
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/configuration/foo1', 'value': 'bar1',
                                     'op': 'add'},
                                    {'path': '/configuration/foo2', 'value': 'bar2',
                                     'op': 'add'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)
        result = self.get_json('/bricks/%s' % cdict['uuid'])
        expected = {"foo1": "bar1", "foo2": "bar2", "test": "test"}
        self.assertEqual(expected, result['configuration'])

    def test_remove_uuid(self):
        cdict = apiutils.get_test_brick_json()
        response = self.patch_json('/bricks/%s' % cdict['uuid'],
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(base.FunctionalTest):

    @mock.patch.object(timeutils, 'utcnow')
    def test_create_brick(self, mock_utcnow):
        cdict = apiutils.get_test_brick_json()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        with mock.patch(
            'bricks.conductor.rpcapi.ConductorAPI.do_brick_deploy'
        ) as do_brick_deploy:
            do_brick_deploy.return_value = 'yep'

            response = self.post_json('/bricks', cdict)
            self.assertEqual(201, response.status_int)
            result = self.get_json('/bricks/%s' % cdict['uuid'])
            self.assertEqual(cdict['uuid'], result['uuid'])
            self.assertFalse(result['updated_at'])
            return_created_at = timeutils.parse_isotime(result['created_at']).replace(tzinfo=None)
            self.assertEqual(test_time, return_created_at)

            # assert that the deploy task has been started.
            self.assertEqual(1, do_brick_deploy.call_count)

    def test_create_brick_generate_uuid(self):
        cdict = apiutils.get_test_brick_json()
        del cdict['uuid']
        self.post_json('/bricks', cdict)
        result = self.get_json('/bricks')
        self.assertEqual(cdict['status'],
                         result['bricks'][0]['status'])
        self.assertTrue(utils.is_uuid_like(result['bricks'][0]['uuid']))

    def test_create_brick_valid_configuration(self):
        cdict = apiutils.get_test_brick_json(configuration={'foo': 'bar'})
        self.post_json('/bricks', cdict)
        result = self.get_json('/bricks/%s' % cdict['uuid'])
        self.assertEqual(cdict['configuration'], result['configuration'])

    def test_create_brick_invalid_configuration(self):
        cdict = apiutils.get_test_brick_json(configuration={'foo': 123})

        with mock.patch(
            'bricks.conductor.rpcapi.ConductorAPI.do_brick_deploy'
        ) as do_brick_deploy:
            do_brick_deploy.return_value = 'yep'

            response = self.post_json('/bricks', cdict, expect_errors=True)
            self.assertEqual(400, response.status_int)
            self.assertEqual('application/json', response.content_type)
            self.assertTrue(response.json['error_message'])

            # brick deploy should never be called if the object wasn't created
            # successfully.
            self.assertEqual(0, do_brick_deploy.call_count)

    def test_create_brick_unicode_status(self):
        status = u'\u0430\u043c\u043e'
        cdict = apiutils.get_test_brick_json(status=status)
        self.post_json('/bricks', cdict)
        result = self.get_json('/bricks/%s' % cdict['uuid'])
        self.assertEqual(status, result['status'])


class TestDelete(base.FunctionalTest):

    def test_delete_brick(self):
        cdict = dbutils.get_test_brick()
        self.dbapi.create_brick(cdict)
        response = self.delete('/bricks/%s' % cdict['uuid'])
        self.assertEqual(204, response.status_int)

    def test_delete_brick_not_found(self):
        uuid = utils.generate_uuid()
        with mock.patch('bricks.objects.Brick.get_by_uuid',
                        side_effect=exception.BrickNotFound(uuid)):
            response = self.delete('/bricks/%s' % uuid, expect_errors=True)
            self.assertEqual(404, response.status_int)
            self.assertEqual('application/json', response.content_type)
            self.assertTrue(response.json['error_message'])


class TestStatusUpdate(base.FunctionalTest):

    def test_brick_deploying(self):
        cdict = dbutils.get_test_brick()
        self.dbapi.create_brick(cdict)
        with mock.patch('bricks.conductor.rpcapi.ConductorAPI.do_brick_deploying') \
            as deploying:
            self.post_json('/bricks/%s/status_update' % cdict['uuid'],
                           {'type': states.DEPLOYING}, context=self.context)

            result = self.get_json('/bricks/%s' % cdict['uuid'])
            self.assertEqual(1, deploying.call_count)

    def test_brick_deployfail(self):
        cdict = dbutils.get_test_brick()
        self.dbapi.create_brick(cdict)
        with mock.patch('bricks.conductor.rpcapi.ConductorAPI.do_brick_deployfail') \
            as deployfail:
            self.post_json('/bricks/%s/status_update' % cdict['uuid'],
                           {'type': states.DEPLOYFAIL}, context=self.context)

            result = self.get_json('/bricks/%s' % cdict['uuid'])
            self.assertEqual(1, deployfail.call_count)

    def test_brick_deploydone(self):
        cdict = dbutils.get_test_brick()
        self.dbapi.create_brick(cdict)
        with mock.patch('bricks.conductor.rpcapi.ConductorAPI.do_brick_deploydone') \
            as deploydone:
            self.post_json('/bricks/%s/status_update' % cdict['uuid'],
                           {'type': states.DEPLOYDONE}, context=self.context)

            result = self.get_json('/bricks/%s' % cdict['uuid'])
            self.assertEqual(1, deploydone.call_count)
