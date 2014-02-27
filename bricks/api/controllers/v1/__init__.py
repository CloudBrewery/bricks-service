"""
Version 1 of the Bricks API

NOTE: IN PROGRESS AND NOT FULLY IMPLEMENTED.

Should maintain feature parity with Nova Baremetal Extension.

Specification can be found at bricks/doc/api/v1.rst
"""

import pecan
from pecan import rest

from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from bricks.api.controllers.v1 import base
from bricks.api.controllers.v1 import chassis
from bricks.api.controllers.v1 import driver
from bricks.api.controllers.v1 import link
from bricks.api.controllers.v1 import node
from bricks.api.controllers.v1 import port


class MediaType(base.APIBase):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type):
        self.base = base
        self.type = type


class V1(base.APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    "The ID of the version, also acts as the release number"

    media_types = [MediaType]
    "An array of supported media types for this version"

    links = [link.Link]
    "Links that point to a specific URL for this version and documentation"

    chassis = [link.Link]
    "Links to the chassis resource"

    nodes = [link.Link]
    "Links to the nodes resource"

    ports = [link.Link]
    "Links to the ports resource"

    drivers = [link.Link]
    "Links to the drivers resource"

    @classmethod
    def convert(self):
        v1 = V1()
        v1.id = "v1"
        v1.links = [link.Link.make_link('self', pecan.request.host_url,
                                        'v1', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        'http://docs.openstack.org',
                                        'developer/bricks/dev',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')
        ]
        v1.media_types = [MediaType('application/json',
                          'application/vnd.openstack.bricks.v1+json')]
        v1.chassis = [link.Link.make_link('self', pecan.request.host_url,
                                          'chassis', ''),
                      link.Link.make_link('bookmark',
                                           pecan.request.host_url,
                                           'chassis', '',
                                           bookmark=True)
        ]
        v1.nodes = [link.Link.make_link('self', pecan.request.host_url,
                                        'nodes', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'nodes', '',
                                        bookmark=True)
        ]
        v1.ports = [link.Link.make_link('self', pecan.request.host_url,
                                        'ports', ''),
                    link.Link.make_link('bookmark',
                                        pecan.request.host_url,
                                        'ports', '',
                                        bookmark=True)
        ]
        v1.drivers = [link.Link.make_link('self', pecan.request.host_url,
                                          'drivers', ''),
                      link.Link.make_link('bookmark',
                                          pecan.request.host_url,
                                          'drivers', '',
                                          bookmark=True)
        ]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    nodes = node.NodesController()
    ports = port.PortsController()
    chassis = chassis.ChassisController()
    drivers = driver.DriversController()

    @wsme_pecan.wsexpose(V1)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return V1.convert()

__all__ = (Controller)
