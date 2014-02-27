# -*- encoding: utf-8 -*-

import pecan
from pecan import rest

from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from bricks.api.controllers import v1
from bricks.api.controllers.v1 import base
from bricks.api.controllers.v1 import link


class Version(base.APIBase):
    """An API version representation."""

    id = wtypes.text
    "The ID of the version, also acts as the release number"

    links = [link.Link]
    "A Link that point to a specific version of the API"

    @classmethod
    def convert(self, id):
        version = Version()
        version.id = id
        version.links = [link.Link.make_link('self', pecan.request.host_url,
                                             id, '', bookmark=True)]
        return version


class Root(base.APIBase):

    name = wtypes.text
    "The name of the API"

    description = wtypes.text
    "Some information about this API"

    versions = [Version]
    "Links to all the versions available in this API"

    default_version = Version
    "A link to the default version of the API"

    @classmethod
    def convert(self):
        root = Root()
        root.name = "OpenStack Bricks API"
        root.description = ("Bricks is an OpenStack project which aims to "
                            "provision configuration to instances.")
        root.versions = [Version.convert('v1')]
        root.default_version = Version.convert('v1')
        return root


class RootController(rest.RestController):

    _versions = ['v1']
    "All supported API versions"

    _default_version = 'v1'
    "The default API version"

    v1 = v1.Controller()

    @wsme_pecan.wsexpose(Root)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return Root.convert()

    @pecan.expose()
    def _route(self, args):
        """Overrides the default routing behavior.

        It redirects the request to the default version of the bricks API
        if the version number is not specified in the url.
        """

        if args[0] and args[0] not in self._versions:
            args = [self._default_version] + args
        return super(RootController, self)._route(args)
