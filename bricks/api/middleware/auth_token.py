from keystoneclient.middleware import auth_token

from bricks.common import utils


class AuthTokenMiddleware(auth_token.AuthProtocol):
    """A wrapper on Keystone auth_token middleware.

    Does not perform verification of authentication tokens
    for public routes in the API.

    """
    def __init__(self, app, conf, public_api_routes=[]):
        self.public_api_routes = set(public_api_routes)

        super(AuthTokenMiddleware, self).__init__(app, conf)

    def __call__(self, env, start_response):
        path = utils.safe_rstrip(env.get('PATH_INFO'), '/')

        if path in self.public_api_routes:
            return self.app(env, start_response)

        return super(AuthTokenMiddleware, self).__call__(env, start_response)
