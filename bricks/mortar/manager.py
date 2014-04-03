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
from bricks.conductor import rpcapi as conductor_rpcapi
from bricks.objects import base as objects_base
from bricks.openstack.common import lockutils
from bricks.openstack.common import log

from bricks.mortar import utils

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
        self.conductor_rpcapi = conductor_rpcapi.ConductorAPI()

        # GreenPool of background workers for performing tasks async.
        self._worker_pool = greenpool.GreenPool(size=CONF.rpc_thread_pool_size)

    def initialize_service_hook(self, service):
        pass

    def do_ping(self, context, notification=None):
        LOG.debug(_('Received notification: %r') %
                  notification.get('event_type'))

    def do_execute(self, context, execution_task, topic=None):
        """Pass along the execution list to the execution driver for further
        processing.
        """
        def worker_callback(gt, *args, **kwargs):
            self.conductor_rpcapi.do_report_last_task(
                context, execution_task.instance_id, gt.wait())

        if execution_task.instance_id in utils.get_running_instances():
            LOG.debug('received some things to do for %s',
                      execution_task.instance_id)
            worker = self._spawn_worker(utils.do_execute, context,
                                        execution_task)
            worker.link(worker_callback)

    def do_check_instances(self, context, instance_list, topic=None):
        """Do a health check on instances, and report back over rmq the
        health of any that you know about.
        """
        LOG.debug('Doing health Check, as commanded by my conductor.')

        def worker_cb(gt, *args, **kwargs):
            self.conductor_rpcapi.do_task_report(context, gt.wait())

        worker = self._spawn_worker(utils.do_health_check, context,
                                    instance_list)
        worker.link(worker_cb)

    def do_check_last_task(self, context, instance_id, topic=None):
        """Check the state of the last run task on an instance and return
        to the conductor
        """
        LOG.debug('Checking on instance %s.' % instance_id)

        def worker_callback(gt, *args, **kwargs):
            self.conductor_rpcapi.do_report_last_task(context,
                                                      instance_id, gt.wait())

        worker = self._spawn_worker(utils.do_check_last_task, context,
                                    instance_id)
        worker.link(worker_callback)

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    @lockutils.synchronized(WORKER_SPAWN_lOCK, 'bricks-mortar-')
    def _spawn_worker(self, func, *args, **kwargs):
        """Create a greenthread to run func(*args, **kwargs).
        """
        if self._worker_pool.free():
            return self._worker_pool.spawn(func, *args, **kwargs)
        else:
            raise exception.NoFreeConductorWorker()
