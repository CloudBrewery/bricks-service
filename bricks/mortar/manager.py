"""
The squishy bits that run on the Nova Compute instances, a sort of conductor
agent.

A single instance of :py:class:`bricks.mortar.manager.MortarManager` is
created within the *bricks-mortar* process, and is responsible for
performing updates or executing things on agents
"""

from eventlet import greenpool

from oslo.config import cfg

from bricks.common import exception
from bricks.common import service
from bricks.db import api as dbapi
from bricks.objects import base as objects_base
from bricks.openstack.common import lockutils
from bricks.openstack.common import log

MANAGER_TOPIC = 'bricks.mortar_manager'
WORKER_SPAWN_lOCK = "mortar_worker_spawn"


LOG = log.getLogger(__name__)

mortar_opts = [
    cfg.StrOpt('api_url',
               default=None,
               help=('URL of Bricks API service. If not set bricks can '
                     'get the current value from the keystone service '
                     'catalog.')),
    cfg.IntOpt('heartbeat_interval',
               default=10,
               help='Seconds between mortar service heart beats.'),
    cfg.IntOpt('heartbeat_timeout',
               default=60,
               help='Maximum time (in seconds) since the last check-in '
                    'of a mortar.'),
]

CONF = cfg.CONF
CONF.register_opts(mortar_opts, 'mortar')


class MortarManager(service.PeriodicService):
    """Bricks Mortar service main class."""

    RPC_API_VERSION = '1.0'

    def __init__(self, host, topic):
        serializer = objects_base.BricksObjectSerializer()
        super(MortarManager, self).__init__(host, topic,
                                            serializer=serializer)

    def start(self):
        super(MortarManager, self).start()
        self.dbapi = dbapi.get_instance()

        # GreenPool of background workers for performing tasks async.
        self._worker_pool = greenpool.GreenPool(size=CONF.rpc_thread_pool_size)

    def initialize_service_hook(self, service):
        pass

    def do_ping(self, context, notification=None):
        LOG.debug(_('Received notification: %r') %
                  notification.get('event_type'))

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    def do_execute(self, context, execution_list, topic=None):
        LOG.debug('received some things to do!', execution_list)

    @lockutils.synchronized(WORKER_SPAWN_lOCK, 'bricks-mortar-')
    def _spawn_worker(self, func, *args, **kwargs):
        """Create a greenthread to run func(*args, **kwargs).
        """
        if self._worker_pool.free():
            return self._worker_pool.spawn(func, *args, **kwargs)
        else:
            raise exception.NoFreeConductorWorker()
