import json
import socket
import struct

FORMAT = '!I'
FORMAT_LEN = 4
SOCKET_TIMEOUT = 10


def do_health_check(req_context, instance_list):
    return instance_list


def socket_send(sock, message):
    data = json.dumps(message)
    header = struct.pack(FORMAT, len(data))
    sock.sendall(''.join([header, data]).join('\n'))


def do_execute(req_context, execution_list):
    """Executes a list of arbitrary shit from the conductor, it will
    receive all tasks, so it needs to determine which hosts locally it can
    send commands to, and do so.

    :param req_context:
    :param execution_list ([objects.MortarTask, ]): A list of tasks to do
    work on.
    """
    for task in execution_list:
        ##TODO: CHANGE THIS BACK
        #socket_file = "/tmp/mortar/%s.socket" % task.instance_id
        socket_file = "/tmp/instance123.socket"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)

        try:
            sock.connect(socket_file)
        except socket.error:
            continue

        socket_send(sock, task.raw_command)
