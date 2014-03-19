from bricks.db import api as dbapi
from bricks.objects import base
from bricks.objects import utils


class BrickConfig(base.BricksObject):
    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': utils.str_or_none,
        'name': utils.str_or_none,
        'version': utils.str_or_none,
        'is_public': bool,
        'tenant_id': utils.str_or_none,

        'tag': utils.str_or_none,
        'description': utils.str_or_none,
        'logo': utils.str_or_none,
        'app_version': utils.str_or_none,

        'ports': utils.list_or_none,
        'environ': utils.dict_or_none,
        'email_template': utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(brickconfig, db_brickconfig):
        """Converts a database entity to a formal object."""
        for field in brickconfig.fields:
            brickconfig[field] = db_brickconfig[field]

        brickconfig.obj_reset_changes()
        return brickconfig

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid=None):
        """Find a brickconfig based on uuid and return a BrickConfig
        object.

        :param uuid: the uuid of a brickconfig.
        :returns: a :class:`BrickConfig` object.
        """
        db_brickconfig = cls.dbapi.get_brickconfig(uuid)
        return BrickConfig._from_db_object(cls(), db_brickconfig)

    @base.remotable
    def save(self, context):
        """Save updates to this BrickConfig.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context
        """
        updates = self.obj_get_changes()
        self.dbapi.update_brickconfig(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context):
        """Loads updates for this BrickConfig.

        Loads a brickconfig with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded brickconfig column by column, if there are any updates.

        :param context: Security context
        """
        current = self.__class__.get_by_uuid(context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
