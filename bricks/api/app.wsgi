# -*- mode: python -*-
# -*- encoding: utf-8 -*-
"""
Use this file for deploying the API service under Apache2 mod_wsgi.
"""

from bricks.api import app
from bricks.common import service
from bricks.openstack.common import gettextutils

gettextutils.install('bricks')

service.prepare_service([])

application = app.VersionSelectorApplication()
