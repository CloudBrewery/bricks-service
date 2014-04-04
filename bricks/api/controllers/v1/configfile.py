import datetime

import jsonpatch
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from bricks.api.controllers.v1 import base
from bricks.api.controllers.v1 import collection
from bricks.api.controllers.v1 import link
from bricks.api.controllers.v1 import types
from bricks.api.controllers.v1 import utils as api_utils
from bricks.common import exception
from bricks.common import policy
from bricks import objects
from bricks.openstack.common import excutils
from bricks.openstack.common import log

LOG = log.getLogger(__name__)


def check_policy(context, action, target_obj=None):
    target = {
        'project_id': context.tenant,
        'user_id': context.user,
    }
    target.update(target_obj or {})
    _action = 'configfile:%s' % action
    policy.enforce(context, _action, target)


class ConfigFilePatchType(types.JsonPatchType):
    pass


class ConfigFile(base.APIBase):
    """API representation of a configfile.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a
    configfile.
    """

    uuid = types.uuid
    brickconfig_uuid = types.uuid
    name = wtypes.text
    description = wtypes.text
    contents = wtypes.text

    links = [link.Link]

    def __init__(self, **kwargs):
        self.fields = objects.ConfigFile.fields.keys()
        for k in self.fields:
            setattr(self, k, kwargs.get(k))

    @classmethod
    def convert_with_links(cls, rpc_cfgfile, expand=True):
        configfile = ConfigFile(**rpc_cfgfile.as_dict())
        if not expand:
            configfile.unset_fields_except([
                'uuid', 'brickconfig_uuid', 'name', 'description'])

        configfile.links = [
            link.Link.make_link('self', pecan.request.host_url,
                                'configfiles', configfile.uuid),
            link.Link.make_link('bookmark', pecan.request.host_url,
                                'configfiles', configfile.uuid,
                                bookmark=True)
        ]
        return configfile


class ConfigFileCollection(collection.Collection):
    """API representation of a collection of ConfigFiles."""

    configfiles = [ConfigFile]
    "A list containing ports objects"

    def __init__(self, **kwargs):
        self._type = 'configfiles'

    @classmethod
    def convert_with_links(cls, rpc_cfgfiles, limit, url=None,
                           expand=False, **kwargs):
        collection = ConfigFileCollection()
        collection.configfiles = [
            ConfigFile.convert_with_links(bc, expand)
            for bc in rpc_cfgfiles]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.configfiles = [ConfigFile.sample()]
        return sample


class ConfigFileController(rest.RestController):
    """REST controller for ConfigFiles."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_configfile_collection(self, brickconfig_uuid, marker, limit,
                                   sort_key, sort_dir, expand=False,
                                   resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.ConfigFile.get_by_uuid(
                pecan.request.context, marker)

        filters = {}

        if brickconfig_uuid:
            filters['brickconfig_uuid'] = brickconfig_uuid

        configfiles = pecan.request.dbapi.get_configfile_list(
            filters, limit, marker_obj, sort_key=sort_key,
            sort_dir=sort_dir)

        return ConfigFileCollection.convert_with_links(
            configfiles, limit, url=resource_url, expand=expand,
            sort_key=sort_key, sort_dir=sort_dir)

    @wsme_pecan.wsexpose(ConfigFileCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, brickconfig_uuid, marker=None,
                limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of configfiles.

        :param brickconfig_uuid:
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        check_policy(pecan.request.context, 'get_all')
        return self._get_configfile_collection(brickconfig_uuid, marker,
                                               limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(ConfigFileCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, brickconfig_uuid, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of configfiles with detail.

        :param brickconfig_uuid:
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        check_policy(pecan.request.context, 'get_all')
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "configfiles":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['configfiles', 'detail'])
        return self._get_configfile_collection(brickconfig_uuid, marker,
                                               limit, sort_key, sort_dir,
                                               expand, resource_url)

    @wsme_pecan.wsexpose(ConfigFile, types.uuid)
    def get_one(self, configfile_uuid):
        """Retrieve information about the given bc.

        :param configfile_uuid: UUID of a config file.
        """
        check_policy(pecan.request.context, 'get_one')

        rpc_configfile = objects.ConfigFile.get_by_uuid(
            pecan.request.context, configfile_uuid)

        return ConfigFile.convert_with_links(rpc_configfile)

    @wsme_pecan.wsexpose(ConfigFile, body=ConfigFile, status_code=201)
    def post(self, configfile):
        """Create a new Config File.

        :param configfile: a bc within the request body.
        """
        check_policy(pecan.request.context, 'create')

        try:
            new_configfile = pecan.request.dbapi.create_configfile(
                configfile.as_dict())
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.exception(e)
        return ConfigFile.convert_with_links(new_configfile)

    @wsme.validate(types.uuid, [ConfigFilePatchType])
    @wsme_pecan.wsexpose(ConfigFile, types.uuid, body=[ConfigFilePatchType])
    def patch(self, configfile_uuid, patch):
        """Update an existing configfile.

        :param configfile_uuid: UUID of a configfile.
        :param patch: a json PATCH document to apply to this configfile.
        """
        check_policy(pecan.request.context, 'update')

        rpc_configfile = objects.ConfigFile.get_by_uuid(
            pecan.request.context, configfile_uuid)
        try:
            cf = ConfigFile(**jsonpatch.apply_patch(
                rpc_configfile.as_dict(), jsonpatch.JsonPatch(patch)))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.ConfigFile.fields:
            if rpc_configfile[field] != getattr(cf, field):
                rpc_configfile[field] = getattr(cf, field)

        rpc_configfile.save()
        return ConfigFile.convert_with_links(rpc_configfile)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, configfile_uuid):
        """Delete a bc.

        :param configfile_uuid: UUID of a configfile.
        """
        check_policy(pecan.request.context, 'delete')

        pecan.request.dbapi.destroy_configfile(configfile_uuid)
