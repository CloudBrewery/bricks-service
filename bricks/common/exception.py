"""Bricks base exception handling.

Includes decorator for re-raising bricks-type exceptions.

SHOULD include dedicated exception logging.

"""

from oslo.config import cfg
import six

from bricks.openstack.common.gettextutils import _
from bricks.openstack.common import log as logging


LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='Make exception message format errors fatal.'),
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


def _cleanse_dict(original):
    """Strip all admin_password, new_pass, rescue_pass keys from a dict."""
    return dict((k, v) for k, v in original.iteritems() if not "_pass" in k)


class BricksException(Exception):
    """Base Bricks Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs

            except Exception as e:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_('Exception in string format operation'))
                for name, value in kwargs.iteritems():
                    LOG.error("%s: %s" % (name, value))

                if CONF.fatal_exception_format_errors:
                    raise e
                else:
                    # at least get the core message out if something happened
                    message = self.message

        super(BricksException, self).__init__(message)

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class NotAuthorized(BricksException):
    message = _("Not authorized.")
    code = 403


class OperationNotPermitted(NotAuthorized):
    message = _("Operation not permitted.")


class Invalid(BricksException):
    message = _("Unacceptable parameters.")
    code = 400


class Conflict(BricksException):
    message = _('Conflict.')
    code = 409


class TemporaryFailure(BricksException):
    message = _("Resource temporarily unavailable, please retry.")
    code = 503


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class NotFound(BricksException):
    message = _("Resource could not be found.")
    code = 404


class IncompatibleObjectVersion(BricksException):
    message = _('Version %(objver)s of %(objname)s is not supported')


class CatalogUnauthorized(BricksException):
    message = _("Unauthorised for keystone service catalog.")


class CatalogFailure(BricksException):
    pass


class CatalogNotFound(BricksException):
    message = _("Service type %(service_type)s with endpoint type "
                "%(endpoint_type)s not found in keystone service catalog.")


class ServiceUnavailable(BricksException):
    message = _("Connection failed")


class Forbidden(BricksException):
    message = _("Requested OpenStack Images API is forbidden")


class BadRequest(BricksException):
    pass


class InvalidEndpoint(BricksException):
    message = _("The provided endpoint is invalid")


class CommunicationError(BricksException):
    message = _("Unable to communicate with the server.")


class HTTPForbidden(Forbidden):
    pass


class Unauthorized(BricksException):
    pass


class HTTPNotFound(NotFound):
    pass


class ConfigNotFound(BricksException):
    message = _("Could not find config at %(path)s")


class BrickNotFound(NotFound):
    message = _("Coult not find brick %(brick)s")


class BrickConfigNotFound(NotFound):
    message = _("Coult not find brickconfig %(brickconfig)s")
