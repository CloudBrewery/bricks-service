import libvirt


class BricksLibvirt():

    def __init__(self, ro=True, path="qemu:///system"):
        if ro:
            self.conn = libvirt.openReadOnly(path)
        else:
            self.conn = libvirt.open(path)

    def __exit__(self):
        try:
            self.conn.close()
        except Exception:
            pass
