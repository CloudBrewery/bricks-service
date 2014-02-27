import socket

from oslo.config import cfg

CONF = cfg.CONF


def _get_my_ip():
    """Returns the actual ip of the local machine.

    This code figures out what source address would be used if some traffic
    were to be sent out to some well known address on the Internet. In this
    case, a Google DNS server is used, but the specific address does not
    matter much.  No traffic is actually sent.
    """
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(('8.8.8.8', 80))
        (addr, port) = csock.getsockname()
        csock.close()
        return addr
    except socket.error:
        return "127.0.0.1"


netconf_opts = [
    cfg.StrOpt('my_ip',
               default=_get_my_ip(),
               help='IP address of this host.'),
    cfg.BoolOpt('use_ipv6',
                default=False,
                help='Use IPv6.'),
]

CONF.register_opts(netconf_opts)
