# -*- encoding: utf-8 -*-

from bricks.openstack.common import context


class RequestContext(context.RequestContext):
    """Extends security contexts from the OpenStack common library."""

    def __init__(self, auth_token=None, domain_id=None, domain_name=None,
                 user=None, tenant=None, tenant_id=None, is_admin=False,
                 is_public_api=False, read_only=False, show_deleted=False,
                 request_id=None):
        """Stores several additional request parameters:

        :param domain_id: The ID of the domain.
        :param domain_name: The name of the domain.
        :param is_public_api: Specifies whether the request should be processed
                              without authentication.
        :param tenant_id: the tenant's ID

        """
        self.is_public_api = is_public_api
        self.domain_id = domain_id
        self.domain_name = domain_name
        self.tenant_id = tenant_id

        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=user, tenant=tenant,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id)

    def to_dict(self):
        result = {'domain_id': self.domain_id,
                  'domain_name': self.domain_name,
                  'is_public_api': self.is_public_api,
                  'tenant_id': self.tenant_id}

        result.update(super(RequestContext, self).to_dict())

        return result
