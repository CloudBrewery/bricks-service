import grp
import libvirt
from lxml import etree
import os
import pwd
import socket

from bricks.objects import mortar_task

SOCKET_TIMEOUT = 10
INSTANCES_PATH = "/var/lib/nova/instances/"


def get_running_instances():
    conn = libvirt.openReadOnly("qemu:///system")

    libvirt_instances = conn.listAllDomains(
        libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)
    instances = []

    for instance in libvirt_instances:
        instances.append(instance.UUIDString())

    return instances


def config_xml(instance_id):
    xml_path = os.path.join(INSTANCES_PATH, instance_id, 'libvirt.xml')
    xml = etree.parse(xml_path)
    socket_chan = xml.xpath("/devices/channel/target[@name='org.clouda.0']")
    log_chan = xml.xpath("/devices/channel/target[@name='org.clouda.1']")
    devices = xml.find("/devices")
    modified = False

    try:
        os.mkdir(os.path.join(INSTANCES_PATH, 'bricks'))
    except Exception:
        pass

    try:
        uid = pwd.getpwnam("libvirt-qemu").pw_uid
        gid = grp.getgrnam("kvm").gr_uid
        os.chown(os.path.join(INSTANCES_PATH, 'bricks'), uid, gid)
    except Exception:
        pass

    if len(socket_chan) < 1:
        chan = etree.SubElement(devices, "channel")
        chan.attrib["type"] = 'unix'
        source = etree.SubElement(chan, "source")
        source.attrib["mode"] = 'bind'
        source.attrib["path"] = os.path.join(INSTANCES_PATH, instance_id,
                                             'bricks/bricks.socket')
        target = etree.SubElement(chan, "target")
        target.attrib["type"] = 'virtio'
        target.attrib["name"] = 'org.clouda.0'
        address = etree.SubElement(chan, "address")
        address.attrib["type"] = 'virtio-serial'
        address.attrib["controller"] = '0'
        address.attrib["bus"] = '0'
        address.attrib["port"] = '1'
        modified = True

    if len(log_chan) < 1:
        chan = etree.SubElement(devices, "channel")
        chan.attrib["type"] = 'file'
        source = etree.SubElement(chan, "source")
        source.attrib["path"] = os.path.join(INSTANCES_PATH, instance_id,
                                             'bricks/bricks.log')
        target = etree.SubElement(chan, "target")
        target.attrib["type"] = 'virtio'
        target.attrib["name"] = 'org.clouda.1'
        address = etree.SubElement(chan, "address")
        address.attrib["type"] = 'virtio-serial'
        address.attrib["controller"] = '0'
        address.attrib["bus"] = '0'
        address.attrib["port"] = '2'
        modified = True

    if modified:
        xml.write(xml_path, pretty_print=True, xml_declaration=True)

        conn = libvirt.open("qemu:///system")

        libvirt_instances = conn.listAllDomains(
            libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)

        for instance in libvirt_instances:
            if instance.UUIDString() == instance_id:
                instance.destroy()
                instance.undefine()
                break

        instance = conn.defineXML(xml_path)
        instance.create()

    return modified


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
    socket_file = os.path.join(INSTANCES_PATH, task.instance_id,
                               'bricks/bricks.socket')

    if not os.path.exists(socket_file):
        config_xml(task.instance_id)
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
        return mortar_task.ERROR
    finally:
        sock.close()

    return mortar_task.RUNNING


def do_check_last_task(req_context, instance_id):
    """Checks the instance log's last line for a task state

    :param req_context:
    :param instance_id str: An instance ID
    """
    log_file = os.path.join(INSTANCES_PATH, instance_id, 'bricks/bricks.log')

    try:
        log = open(log_file, "r")
    except:
        return mortar_task.INSUFF

    lines = log.readlines()
    line_num = -1
    line = lines[line_num:]

    while line not in mortar_task.STATE_LIST:
        line_num -= 1
        line = lines[line_num]

    if line not in mortar_task.STATE_LIST:
        return mortar_task.INSUFF

    return line
