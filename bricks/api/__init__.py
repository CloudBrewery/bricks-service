# -*- encoding: utf-8 -*-
#
# Copyright © 2014 Cloud A (clouda.ca)
#
# Author: Adam Thurlow <adam@clouda.ca>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo.config import cfg


API_SERVICE_OPTS = [
    cfg.StrOpt('host_ip',
               default='0.0.0.0',
               help='The listen IP for the Bricks API server.'),
    cfg.IntOpt('port',
               default=8119,
               help='The port for the Bricks API server.'),
    cfg.IntOpt('max_limit',
               default=1000,
               help='The maximum number of items returned in a single '
                    'response from a collection resource.'),
]

CONF = cfg.CONF
opt_group = cfg.OptGroup(name='api',
                         title='Options for the bricks-api service')
CONF.register_group(opt_group)
CONF.register_opts(API_SERVICE_OPTS, opt_group)
