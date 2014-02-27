# -*- encoding: utf-8 -*-
"""The Bricks Service API."""

import logging
import sys

from oslo.config import cfg
from six.moves import socketserver
from wsgiref import simple_server

from bricks.api import app
from bricks.common import service as bricks_service
from bricks.openstack.common import log

CONF = cfg.CONF


class ThreadedSimpleServer(socketserver.ThreadingMixIn,
                           simple_server.WSGIServer):
    """A Mixin class to make the API service greenthread-able."""
    pass


def main():
    # Pase config file and command line options, then start logging
    bricks_service.prepare_service(sys.argv)

    # Build and start the WSGI app
    host = CONF.api.host_ip
    port = CONF.api.port
    wsgi = simple_server.make_server(
        host, port,
        app.VersionSelectorApplication(),
        server_class=ThreadedSimpleServer)

    LOG = log.getLogger(__name__)
    LOG.info(_("Serving on http://%(host)s:%(port)s") %
             {'host': host, 'port': port})
    LOG.info(_("Configuration:"))
    CONF.log_opt_values(LOG, logging.INFO)

    try:
        wsgi.serve_forever()
    except KeyboardInterrupt:
        pass
