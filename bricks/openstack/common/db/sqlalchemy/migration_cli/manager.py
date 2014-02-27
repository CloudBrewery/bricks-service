#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from stevedore import enabled


MIGRATION_NAMESPACE = 'bricks.openstack.common.migration'


def check_plugin_enabled(ext):
    """Used for EnabledExtensionManager"""
    return ext.obj.enabled


class MigrationManager(object):

    def __init__(self, migration_config):
        self._manager = enabled.EnabledExtensionManager(
            MIGRATION_NAMESPACE,
            check_plugin_enabled,
            invoke_kwds={'migration_config': migration_config},
            invoke_on_load=True
        )
        if not self._plugins:
            raise ValueError('There must be at least one plugin active.')

    @property
    def _plugins(self):
        return sorted(ext.obj for ext in self._manager.extensions)

    def upgrade(self, revision):
        """Upgrade database with all available backends."""
        results = []
        for plugin in self._plugins:
            results.append(plugin.upgrade(revision))
        return results

    def downgrade(self, revision):
        """Downgrade database with available backends."""
        #downgrading should be performed in reversed order
        results = []
        for plugin in reversed(self._plugins):
            results.append(plugin.downgrade(revision))
        return results

    def version(self):
        """Return last version of db."""
        last = None
        for plugin in self._plugins:
            version = plugin.version()
            if version:
                last = version
        return last

    def revision(self, message, autogenerate):
        """Generate template or autogenerated revision."""
        #revision should be done only by last plugin
        return self._plugins[-1].revision(message, autogenerate)

    def stamp(self, revision):
        """Create stamp for a given revision."""
        return self._plugins[-1].stamp(revision)
