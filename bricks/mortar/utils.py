import os
import socket

SOCKET_TIMEOUT = 10
SOCKET_PATH_PREFIX = "/tmp/bricks/"
LOG_PATH_PREFIX = "/var/log/bricks/instances/"
STATES = ['TASK-COMPLETE', 'TASK-ERROR', 'TASK-RUNNING', 'INSUFFICIENT-DATA']


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
    #socket_file = os.path.join(SOCKET_PATH_PREFIX, task.instance_id, '.socket')
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


def do_check_last_task(req_context, instance_id):
    """Checks the instance log's last line for a task state

    :param req_context:
    :param instance_id str: An instance ID
    """
    log_file = os.path.join(LOG_PATH_PREFIX, instance_id, '.log')

    try:
        log = open(log_file, "r")
    except:
        return 'INSUFFICIENT-DATA'

    lines = log.readlines()
    line_num = -1
    line = lines[line_num:]

    while line not in STATES:
        line_num -= 1
        line = lines[line_num]

    if line not in STATES:
        return 'INSUFFICIENT-DATA'

    return line
