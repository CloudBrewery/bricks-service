import os
import socket

FORMAT = '!I'
FORMAT_LEN = 4
SOCKET_TIMEOUT = 10


def do_health_check(req_context, instance_list):
    return instance_list


def socket_send(sock, message, filename=None):
    sock.sendall(''.join('BOF %s\n' % filename).join(message).join('EOF\n'))


def do_execute(req_context, task):
    """Executes a list of arbitrary shit from the conductor, it will
    receive all tasks, so it needs to determine which hosts locally it can
    send commands to, and do so.

    :param req_context:
    :param execution_list ([objects.MortarTask, ]): A list of tasks to do
    work on.
    """
    ##TODO: CHANGE THIS BACK
    #socket_file = "/tmp/mortar/%s.socket" % task.instance_id
    socket_file = "/tmp/instance123.socket"

    if not os.path.exists(socket_file):
        return

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect(socket_file)
        sock.sendall("StartStream\n")
        for filename, contents in task.configuration:
            socket_send(sock, contents, filename=filename)
        sock.sendall("StopStream\n")
    except socket.error:
        pass
    finally:
        sock.close()
