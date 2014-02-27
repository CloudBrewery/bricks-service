"""
Conduct all activity related to Brick deployments

A single instance of :py:class:`bricks.conductor.manager.ConductorManager` is
created within the *bricks-conductor* process, and is responsible for
performing all actions on resources .

Commands are received via RPC calls. The conductor service also performs
periodic tasks, eg. to monitor the status of active deployments.

Drivers are loaded via entrypoints by the
:py:class:`bricks.common.driver_factory` class. Each driver is instantiated
only once, when the ConductorManager service starts.  In this way, a single
ConductorManager may use multiple drivers, and manage heterogeneous hardware.

When multiple :py:class:`ConductorManager` are run on different hosts, they are
all active and cooperatively manage all nodes in the deployment.  Nodes are
locked by each conductor when performing actions which change the state of that
node; these locks are represented by the
:py:class:`bricks.conductor.task_manager.TaskManager` class.

A :py:class:`bricks.common.hash_ring.HashRing` is used to distribute nodes
across the set of active conductors which support each node's driver.
Rebalancing this ring can trigger various actions by each conductor, such as
building or tearing down the TFTP environment for a node, notifying Neutron of
a change, etc.
"""

from eventlet import greenpool

from oslo.config import cfg

from ironic.common import driver_factory
from ironic.common import exception
from ironic.common import hash_ring as hash
from ironic.common import service
from ironic.common import states
from ironic.conductor import task_manager
from ironic.conductor import utils
from ironic.db import api as dbapi
from ironic.objects import base as objects_base
from ironic.openstack.common import excutils
from ironic.openstack.common import lockutils
from ironic.openstack.common import log
from ironic.openstack.common import periodic_task

MANAGER_TOPIC = 'ironic.conductor_manager'
WORKER_SPAWN_lOCK = "conductor_worker_spawn"

LOG = log.getLogger(__name__)

conductor_opts = [
        cfg.StrOpt('api_url',
                   default=None,
                   help=('URL of Bricks API service. If not set bricks can '
                         'get the current value from the keystone service '
                         'catalog.')),
        cfg.IntOpt('heartbeat_interval',
                   default=10,
                   help='Seconds between conductor heart beats.'),
        cfg.IntOpt('heartbeat_timeout',
                   default=60,
                   help='Maximum time (in seconds) since the last check-in '
                        'of a conductor.'),
        cfg.IntOpt('sync_power_state_interval',
                   default=60,
                   help='Interval between syncing the node power state to the '
                        'database, in seconds.'),
]

CONF = cfg.CONF
CONF.register_opts(conductor_opts, 'conductor')


class ConductorManager(service.PeriodicService):
    """Bricks Conductor service main class."""

    RPC_API_VERSION = '1.9'

    def __init__(self, host, topic):
        serializer = objects_base.IronicObjectSerializer()
        super(ConductorManager, self).__init__(host, topic,
                                               serializer=serializer)

    def start(self):
        super(ConductorManager, self).start()
        self.dbapi = dbapi.get_instance()

        # create a DriverFactory instance, which initializes the stevedore
        # extension manager, when the service starts.
        # TODO(deva): Enable re-loading of the DriverFactory to load new
        #             extensions without restarting the whole service.
        df = driver_factory.DriverFactory()
        self.drivers = df.names
        """List of driver names which this conductor supports."""

        try:
            self.dbapi.register_conductor({'hostname': self.host,
                                           'drivers': self.drivers})
        except exception.ConductorAlreadyRegistered:
            LOG.warn(_("A conductor with hostname %(hostname)s "
                       "was previously registered. Updating registration")
                       % {'hostname': self.host})
            self.dbapi.unregister_conductor(self.host)
            self.dbapi.register_conductor({'hostname': self.host,
                                           'drivers': self.drivers})

        self.driver_rings = self._get_current_driver_rings()
        """Consistent hash ring which maps drivers to conductors."""

        self._worker_pool = greenpool.GreenPool(size=CONF.rpc_thread_pool_size)
        """GreenPool of background workers for performing tasks async."""

    # TODO(deva): add stop() to call unregister_conductor

    def initialize_service_hook(self, service):
        pass

    def process_notification(self, notification):
        LOG.debug(_('Received notification: %r') %
                        notification.get('event_type'))
        # TODO(deva)

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    def get_node_power_state(self, context, node_id):
        """Get and return the power state for a single node."""

        with task_manager.acquire(context, [node_id], shared=True) as task:
            node = task.resources[0].node
            driver = task.resources[0].driver
            state = driver.power.get_power_state(task, node)
            return state

    def update_node(self, context, node_obj):
        """Update a node with the supplied data.

        This method is the main "hub" for PUT and PATCH requests in the API.
        It ensures that the requested change is safe to perform,
        validates the parameters with the node's driver, if necessary.

        :param context: an admin context
        :param node_obj: a changed (but not saved) node object.

        """
        node_id = node_obj.uuid
        LOG.debug(_("RPC update_node called for node %s.") % node_id)

    def change_node_power_state(self, context, node_id, new_state):
        """RPC method to encapsulate changes to a node's state.

        Perform actions such as power on, power off. The validation and power
        action are performed in background (async). Once the power action is
        finished and successful, it updates the power_state for the node with
        the new power state.

        :param context: an admin context.
        :param node_id: the id or uuid of a node.
        :param new_state: the desired power state of the node.
        :raises: NoFreeConductorWorker when there is no free worker to start
                 async task.

        """
        LOG.debug(_("RPC change_node_power_state called for node %(node)s. "
                    "The desired new state is %(state)s.")
                    % {'node': node_id, 'state': new_state})

    def validate_vendor_action(self, context, node_id, driver_method, info):
        """Validate driver specific info or get driver status."""

        LOG.debug(_("RPC validate_vendor_action called for node %s.")
                    % node_id)

    def do_vendor_action(self, context, node_id, driver_method, info):
        """Run driver action asynchronously."""

        with task_manager.acquire(context, node_id, shared=True) as task:
                task.driver.vendor.vendor_passthru(task, task.node,
                                                  method=driver_method, **info)

    def do_node_deploy(self, context, node_id):
        """RPC method to initiate deployment to a node.

        :param context: an admin context.
        :param node_id: the id or uuid of a node.
        :raises: InstanceDeployFailure

        """
        LOG.debug(_("RPC do_node_deploy called for node %s.") % node_id)

    def do_node_tear_down(self, context, node_id):
        """RPC method to tear down an existing node deployment.

        :param context: an admin context.
        :param node_id: the id or uuid of a node.
        :raises: InstanceDeployFailure

        """
        LOG.debug(_("RPC do_node_tear_down called for node %s.") % node_id)

    @periodic_task.periodic_task(spacing=CONF.conductor.heartbeat_interval)
    def _conductor_service_record_keepalive(self, context):
        self.dbapi.touch_conductor(self.host)

    @periodic_task.periodic_task(spacing=CONF.conductor.sync_power_state_interval)
    def _sync_power_states(self, context):
        filters = {'reserved': False}
        columns = ['id', 'uuid', 'driver']
        node_list = self.dbapi.get_nodeinfo_list(columns=columns,
                                                 filters=filters)
        for (node_id, node_uuid, driver) in node_list:
            # only sync power states for nodes mapped to this conductor
            mapped_hosts = self.driver_rings[driver].get_hosts(node_uuid)
            if self.host not in mapped_hosts:
                continue

            try:
                # prevent nodes in DEPLOYWAIT state from locking
                node = self.dbapi.get_node(node_uuid)
                if node.provision_state == states.DEPLOYWAIT:
                    continue

                with task_manager.acquire(context, node_id) as task:
                    node = task.node

                    try:
                        power_state = task.driver.power.get_power_state(task,
                                                                        node)
                    except Exception as e:
                        #TODO(rloo): change to IronicException, after
                        # https://bugs.launchpad.net/ironic/+bug/1267693
                        LOG.debug(_("During sync_power_state, could not get "
                            "power state for node %(node)s. Error: %(err)s.") %
                            {'node': node.uuid, 'err': e})
                        continue

                    if power_state != node['power_state']:
                        # NOTE(deva): don't log a warning the first time we
                        #             sync a node's power state
                        if node['power_state'] is not None:
                            LOG.warning(_("During sync_power_state, node "
                                "%(node)s out of sync. Expected: %(old)s. "
                                "Actual: %(new)s. Updating DB.") %
                                {'node': node['uuid'],
                                 'old': node['power_state'],
                                 'new': power_state})
                        node['power_state'] = power_state
                        node.save(context)

            except exception.NodeNotFound:
                LOG.info(_("During sync_power_state, node %(node)s was not "
                           "found and presumed deleted by another process.") %
                           {'node': node_uuid})
                continue
            except exception.NodeLocked:
                LOG.info(_("During sync_power_state, node %(node)s was "
                           "already locked by another process. Skip.") %
                           {'node': node_uuid})
                continue

    def _get_current_driver_rings(self):
        """Build the current hash ring for this ConductorManager's drivers."""
        pass

    def rebalance_node_ring(self):
        """Perform any actions necessary when rebalancing the consistent hash.

        This may trigger several actions, such as calling driver.deploy.prepare
        for nodes which are now mapped to this conductor.

        """
        # TODO(deva): implement this
        pass

    def validate_driver_interfaces(self, context, node_id):
        """Validate the `core` and `standardized` interfaces for drivers.

        :param context: request context.
        :param node_id: node id or uuid.
        :returns: a dictionary containing the results of each
                  interface validation.

        """
        LOG.debug(_('RPC validate_driver_interfaces called for node %s.') %
                    node_id)

    def change_node_maintenance_mode(self, context, node_id, mode):
        """Set node maintenance mode on or off.

        :param context: request context.
        :param node_id: node id or uuid.
        :param mode: True or False.
        :raises: NodeMaintenanceFailure

        """
        LOG.debug(_("RPC change_node_maintenance_mode called for node %(node)s"
                    " with maintanence mode: %(mode)s") % {'node': node_id,
                                                           'mode': mode})

    @lockutils.synchronized(WORKER_SPAWN_lOCK, 'bricks-')
    def _spawn_worker(self, func, *args, **kwargs):

        """Create a greenthread to run func(*args, **kwargs).

        Spawns a greenthread if there are free slots in pool, otherwise raises
        exception. Execution control returns immediately to the caller.

        :returns: GreenThread object.
        :raises: NoFreeConductorWorker if worker pool is currently full.

        """
        if self._worker_pool.free():
            return self._worker_pool.spawn(func, *args, **kwargs)
        else:
            raise exception.NoFreeConductorWorker()

    def destroy_node(self, context, node_id):
        """Delete a node.

        :param context: request context.
        :param node_id: node id or uuid.
        :raises: NodeLocked if node is locked by another conductor.
        :raises: NodeAssociated if the node contains an instance
            associated with it.

        """
        pass

