import grp
import libvirt
from lxml import etree
import os
import pwd
import socket
from time import sleep

from bricks.objects import mortar_task
from bricks.openstack.common import log

SOCKET_TIMEOUT = 10
INSTANCES_PATH = "/var/lib/nova/instances/"

LOG = log.getLogger(__name__)


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
    socket_chan_check = xml.xpath("/devices/channel/target[@name='org.clouda.0']")
    log_chan_check = xml.xpath("/devices/channel/target[@name='org.clouda.1']")
    devices = xml.find("/devices")
    modified = False

    if len(socket_chan_check) < 1:
        sock_chan = etree.SubElement(devices, "channel")
        sock_chan.attrib["type"] = 'unix'
        source = etree.SubElement(sock_chan, "source")
        source.attrib["mode"] = 'bind'
        source.attrib["path"] = os.path.join(INSTANCES_PATH, instance_id,
                                             'bricks/bricks.socket')
        target = etree.SubElement(sock_chan, "target")
        target.attrib["type"] = 'virtio'
        target.attrib["name"] = 'org.clouda.0'
        address = etree.SubElement(sock_chan, "address")
        address.attrib["type"] = 'virtio-serial'
        address.attrib["controller"] = '0'
        address.attrib["bus"] = '0'
        address.attrib["port"] = '1'
        modified = True

    if len(log_chan_check) < 1:
        log_chan = etree.SubElement(devices, "channel")
        log_chan.attrib["type"] = 'file'
        source = etree.SubElement(log_chan, "source")
        source.attrib["path"] = os.path.join(INSTANCES_PATH, instance_id,
                                             'bricks/bricks.log')
        target = etree.SubElement(log_chan, "target")
        target.attrib["type"] = 'virtio'
        target.attrib["name"] = 'org.clouda.1'
        address = etree.SubElement(log_chan, "address")
        address.attrib["type"] = 'virtio-serial'
        address.attrib["controller"] = '0'
        address.attrib["bus"] = '0'
        address.attrib["port"] = '2'
        modified = True

    if modified:
        try:
            os.mkdir(os.path.join(INSTANCES_PATH, instance_id, 'bricks'))
        except Exception:
            pass

        try:
            uid = pwd.getpwnam("libvirt-qemu").pw_uid
            gid = grp.getgrnam("kvm").gr_gid
            os.chown(os.path.join(INSTANCES_PATH, instance_id, 'bricks'),
                     uid, gid)
        except Exception:
            pass

        conn = libvirt.open("qemu:///system")

        try:
            instance = conn.lookupByUUIDString(instance_id)
        except Exception:
            return False

        ret = instance.shutdown()
        LOG.debug(ret)

        maxwait = 15
        mywait = 0
        waiting = True
        LOG.debug("waiting for VM to shut down")
        while waiting and mywait < maxwait:
            sleep(3)
            mywait += 3
            off_instances = conn.listAllDomains(
                    libvirt.VIR_CONNECT_LIST_DOMAINS_SHUTOFF)
            LOG.debug("These are off: %s" % [off.UUIDString() for off in off_instances])
            waiting = instance_id not in [x.UUIDString() for x in off_instances]

        if waiting:
            return False

        instance = conn.defineXML(etree.tostring(xml, pretty_print=True))
        instance.create()

        xml.write(xml_path, pretty_print=True, xml_declaration=True)

    return modified


def do_health_check(req_context, instance_list):
    return instance_list


def socket_send(sock, message, filename=None):
    sock.sendall('\n'.join(['BOF %s\n' % filename, message, 'EOF\n']))


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

    conn = libvirt.open("qemu:///system")
    if not instance_started(task.instance_id, conn=conn):
        start_instance(task.instance_id, conn=conn)

    if not cloud_init_finished(task.instance_id):
        return

    if not os.path.exists(socket_file):
        if task.instance_id in get_running_instances():
            LOG.debug("%s does not have proper XML. Configuring..." %
                      task.instance_id)
            config_xml(task.instance_id)
        return

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect(socket_file)
        LOG.debug("Starting stream on task for %s" % task.instance_id)
        sock.sendall("StartStream\n")
        for filename, contents in task.configuration.iteritems():
            LOG.debug("Stream file %s with contents %s" % (filename, contents))
            socket_send(sock, contents, filename=filename)
        LOG.debug("Done streaming task for %s" % task.instance_id)
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
    log_file = os.path.join(INSTANCES_PATH, instance_id,
                            'bricks', 'bricks.log')

    try:
        log = open(log_file, "r")
    except Exception, e:
        LOG.debug("Unable to open log file %s" % log_file)
        LOG.debug(e)
        return mortar_task.INSUFF

    lines = log.readlines()
    lines.reverse()
    for line in lines:
        LOG.debug(line)
        _line = line.strip()
        if _line in mortar_task.STATE_LIST:
            return _line

    return mortar_task.INSUFF


def cloud_init_finished(instance_id):
    "checks whether cloud init ias finisiehd for a user"
    log_file = os.path.join(INSTANCES_PATH, instance_id, 'console.log')
    with open(log_file, 'r') as l:
        for line in l.readlines():
            if 'cloud-init boot finished' in line:
                LOG.debug("Clout init complete for instance")
                return True
    return False


def instance_started(instance_id, conn=None):
    conn = conn or libvirt.open("qemu:///system")
    try:
        instance = conn.lookupByUUIDString(instance_id)
        return instance.isActive()
    except Exception, e:
        LOG.warning("failed to check if instance is started %s" % e.message)
        return False


def start_instance(instance_id, conn=None):
    conn = conn or libvirt.open("qemu:///system")
    try:
        instance = conn.lookupByUUIDString(instance_id)
        return instance.create()
    except Exception, e:
        LOG.warning("Failed to start instance %s" % e.message)
        return False
