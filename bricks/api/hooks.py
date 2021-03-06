# -*- encoding: utf-8 -*-

from oslo.config import cfg
from pecan import hooks
from webob import exc

from bricks.common import context
from bricks.common import utils
from bricks.conductor import rpcapi
from bricks.db import api as dbapi
from bricks.openstack.common import policy


class ConfigHook(hooks.PecanHook):
    """Attach the config object to the request so controllers can get to it."""

    def before(self, state):
        state.request.cfg = cfg.CONF


class DBHook(hooks.PecanHook):
    """Attach the dbapi object to the request so controllers can get to it."""

    def before(self, state):
        state.request.dbapi = dbapi.get_instance()


class ContextHook(hooks.PecanHook):
    """Configures a request context and attaches it to the request.

    The following HTTP request headers are used:

    X-User-Id or X-User:
        Used for context.user_id.

    X-Tenant-Id or X-Tenant:
        Used for context.tenant.

    X-Auth-Token:
        Used for context.auth_token.

    X-Roles:
        Used for setting context.is_admin flag to either True or False.
        The flag is set to True, if X-Roles contains either an administrator
        or admin substring. Otherwise it is set to False.

    """
    def __init__(self, public_api_routes):
        self.public_api_routes = public_api_routes
        super(ContextHook, self).__init__()

    def before(self, state):
        user_id = state.request.headers.get('X-User-Id')
        user_id = state.request.headers.get('X-User', user_id)
        tenant_id = state.request.headers.get('X-Tenant-Id')
        tenant = state.request.headers.get('X-Tenant', tenant_id)
        domain_id = state.request.headers.get('X-User-Domain-Id')
        domain_name = state.request.headers.get('X-User-Domain-Name')
        auth_token = state.request.headers.get('X-Auth-Token')
        creds = {'roles': state.request.headers.get('X-Roles', '').split(',')}

        is_admin = policy.check('admin', state.request.headers, creds)

        path = utils.safe_rstrip(state.request.path, '/')
        is_public_api = path in self.public_api_routes

        state.request.context = context.RequestContext(
            auth_token=auth_token,
            user=user_id,
            tenant=tenant,
            tenant_id=tenant_id,
            domain_id=domain_id,
            domain_name=domain_name,
            is_admin=is_admin,
            is_public_api=is_public_api)


class RPCHook(hooks.PecanHook):
    """Attach the rpcapi object to the request so controllers can get to it."""

    def before(self, state):
        state.request.rpcapi = rpcapi.ConductorAPI()


class NoExceptionTracebackHook(hooks.PecanHook):
    """Workaround rpc.common: deserialize_remote_exception.

    deserialize_remote_exception builds rpc exception traceback into error
    message which is then sent to the client. Such behavior is a security
    concern so this hook is aimed to cut-off traceback from the error message.

    """
    # NOTE(max_lobur): 'after' hook used instead of 'on_error' because
    # 'on_error' never fired for wsme+pecan pair. wsme @wsexpose decorator
    # catches and handles all the errors, so 'on_error' dedicated for unhandled
    # exceptions never fired.
    def after(self, state):
        # Do not remove traceback when server in debug mode.
        if cfg.CONF.debug:
            return
        # Do nothing if there is no error.
        if 200 <= state.response.status_int < 400:
            return
        # Omit empty body. Some errors may not have body at this level yet.
        if not state.response.body:
            return

        json_body = state.response.json
        faultsting = json_body.get('faultstring')
        traceback_marker = 'Traceback (most recent call last):'
        if faultsting and (traceback_marker in faultsting):
            # Cut-off traceback.
            faultsting = faultsting.split(traceback_marker, 1)[0]
            # Remove trailing newlines and spaces if any.
            json_body['faultstring'] = faultsting.rstrip()
            # Replace the whole json. Cannot change original one beacause it's
            # generated on the fly.
            state.response.json = json_body

