from bricks.db import api as dbapi
from bricks.objects import base
from bricks.objects import utils


class ConfigFile(base.BricksObject):
    dbapi = dbapi.get_instance()

    fields = {
        'id': int,
        'uuid': utils.str_or_none,
        'brickconfig_uuid': utils.str_or_none,
        'name': utils.str_or_none,
        'description': utils.str_or_none,
        'contents': utils.str_or_none,
    }

    @staticmethod
    def _from_db_object(bcf, db_bcf):
        """Converts a database entity to a formal object."""
        for field in bcf.fields:
            bcf[field] = db_bcf[field]

        bcf.obj_reset_changes()
        return bcf

    @base.remotable_classmethod
    def get_by_uuid(cls, context, uuid=None):
        """Find a configfile based on uuid and return a ConfigFile
        object.

        :param uuid: the uuid of a configfile.
        :returns: a :class:`ConfigFile` object.
        """
        db_bcf = cls.dbapi.get_configfile(uuid)
        return ConfigFile._from_db_object(cls(), db_bcf)

    @base.remotable
    def save(self, context):
        """Save updates to this ConfigFile.

        Updates will be made column by column based on the result
        of self.what_changed().

        :param context: Security context
        """
        updates = self.obj_get_changes()
        self.dbapi.update_configfile(self.uuid, updates)

        self.obj_reset_changes()

    @base.remotable
    def refresh(self, context):
        """Loads updates for this ConfigFile.

        Loads a configfile with the same uuid from the database and
        checks for updated attributes. Updates are applied from
        the loaded configfile column by column, if there are any updates.

        :param context: Security context
        """
        current = self.__class__.get_by_uuid(context, uuid=self.uuid)
        for field in self.fields:
            if (hasattr(self, base.get_attrname(field)) and
                    self[field] != current[field]):
                self[field] = current[field]
