"""
Conduct all activity related to Brick deployments

A single instance of :py:class:`bricks.conductor.manager.ConductorManager` is
created within the *bricks-conductor* process, and is responsible for
performing all actions on resources.

Commands are received via RPC calls. The conductor service also performs
periodic tasks, eg. to monitor the status of active deployments.
"""

from eventlet import greenpool

from oslo.config import cfg

from bricks.common import exception
from bricks.common import service
from bricks.common import states
from bricks.db import api as dbapi
from bricks.objects import base as objects_base
from bricks.openstack.common import lockutils
from bricks.openstack.common import log
from bricks.openstack.common import periodic_task

MANAGER_TOPIC = 'bricks.conductor_manager'
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
]

CONF = cfg.CONF
CONF.register_opts(conductor_opts, 'conductor')


class ConductorManager(service.PeriodicService):
    """Bricks Conductor service main class."""

    RPC_API_VERSION = '1.0'

    def __init__(self, host, topic):
        serializer = objects_base.BricksObjectSerializer()
        super(ConductorManager, self).__init__(host, topic,
                                               serializer=serializer)

    def start(self):
        super(ConductorManager, self).start()
        self.dbapi = dbapi.get_instance()

        # GreenPool of background workers for performing tasks async.
        self._worker_pool = greenpool.GreenPool(size=CONF.rpc_thread_pool_size)

    def initialize_service_hook(self, service):
        pass

    def process_notification(self, notification):
        LOG.debug(_('Received notification: %r') %
                        notification.get('event_type'))
        # TODO(deva)

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    @periodic_task.periodic_task(spacing=CONF.conductor.heartbeat_interval)
    def _conductor_service_record_keepalive(self, context):
        self.dbapi.touch_conductor(self.host)

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

