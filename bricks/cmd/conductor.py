# -*- encoding: utf-8 -*-
"""
The Bricks Management Service
"""

import sys

from oslo.config import cfg

from bricks.openstack.common import service

from bricks.common import service as bricks_service
from bricks.conductor import manager

CONF = cfg.CONF


def main():
    # Pase config file and command line options, then start logging
    bricks_service.prepare_service(sys.argv)

    mgr = manager.ConductorManager(CONF.host, manager.MANAGER_TOPIC)
    launcher = service.launch(mgr)
    launcher.wait()
