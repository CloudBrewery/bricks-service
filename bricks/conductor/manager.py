"""
Conduct all activity related to Brick deployments

A single instance of :py:class:`bricks.conductor.manager.ConductorManager` is
created within the *bricks-conductor* process, and is responsible for
performing all actions on resources.
"""

from eventlet import greenpool

from oslo.config import cfg

from bricks.common import exception
from bricks.common import service
from bricks.db import api as dbapi
from bricks.objects import base as objects_base
from bricks.openstack.common import lockutils
from bricks.openstack.common import log
from bricks.openstack.common import periodic_task

from bricks.conductor import utils
from bricks.mortar import rpcapi as mortar_rpcapi

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
        self.mortar_rpcapi = mortar_rpcapi.MortarAPI()

        # GreenPool of background workers for performing tasks async.
        self._worker_pool = greenpool.GreenPool(size=CONF.rpc_thread_pool_size)

    def initialize_service_hook(self, service):
        pass

    def process_notification(self, context, notification=None):
        LOG.debug(_('Received notification: %r') %
                  notification.get('event_type'))

    def periodic_tasks(self, context, raise_on_error=False):
        """Periodic tasks are run at pre-specified interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    def do_brick_deploy(self, context, brick_id, topic=None):
        # utils.brick_deploy_action(context, brick_id)
        self._spawn_worker(utils.brick_deploy_action, context, brick_id)

    def do_brick_deploying(self, context, brick_id, topic=None):
        self._spawn_worker(utils.brick_deploying_action, context, brick_id)

    def do_brick_deployfail(self, context, brick_id, topic=None):
        self._spawn_worker(utils.brick_deployfail_action, context, brick_id)

    def do_brick_deploydone(self, context, brick_id, topic=None):
        self._spawn_worker(utils.brick_deploydone_action, context, brick_id)

    def do_brick_destroy(self, context, brick_id, topic=None):
        self._spawn_worker(utils.brick_destroy_action, context, brick_id)

    def notify_completion(self, context, brick_id, topic=None):
        """Notify the deployer of the brick that the deployment has been
        completed.
        """
        brick = self.dbapi.get_brick(brick_id)
        brickconfig = self.dbapi.get_brickconfig(brick.brickconfig_uuid)
        utils.notify_completion(context, brick, brickconfig)

    @periodic_task.periodic_task(spacing=CONF.conductor.heartbeat_interval)
    def heartbeat_keepalive_all_instances(self, context):
        """Reach out to all instances to get a heartbeat.
        """
        bricks = self.dbapi.get_brick_list()
        instances = [brick.instance_id for brick in bricks]
        self.mortar_rpcapi.do_check_instances(context, instances)

    def do_task_report(self, context, results):
        """Do task results!!!!!!!!!!!!!!!!!!

        Mortar executed some things, now we're hearing back about how those
        things went.
        :param results: ([[instance_id (int),
                           passed (boolean),
                           message (string)], ])
        """
        LOG.debug("received task report from Mortar.")
        pass

    @lockutils.synchronized(WORKER_SPAWN_lOCK, 'bricks-')
    def _spawn_worker(self, func, *args, **kwargs):
        """Create a greenthread to run func(*args, **kwargs).
        """
        if self._worker_pool.free():
            return self._worker_pool.spawn(func, *args, **kwargs)
        else:
            raise exception.NoFreeConductorWorker()
