"""
The Mortar booter.
"""

import sys

from oslo.config import cfg

from bricks.openstack.common import service

from bricks.common import service as bricks_service
from bricks.mortar import manager
from bricks.openstack.common import log

CONF = cfg.CONF


def main():

    LOG = log.getLogger(__name__)
    LOG.info('Launching Mortar!!!')

    # Pase config file and command line options, then start logging
    bricks_service.prepare_service(sys.argv)

    mgr = manager.MortarManager(CONF.host, manager.MANAGER_TOPIC)
    launcher = service.launch(mgr)
    launcher.wait()
    LOG.info('Mortar running. host: %s and topic %s:' % (
        CONF.host, manager.MANAGER_TOPIC))
