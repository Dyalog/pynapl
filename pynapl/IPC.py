# IPC

# On Linux, this is implemented with mkfifo
# On Windows, we use named pipes

from ctypes import *
import platform
import os
import select
import socket
from subprocess import Popen, PIPE
import sys
import tempfile

# use Python 3 types on Python 2
if sys.version_info.major == 2:
    bytes, str = str, unicode

# convert to bytes
def to_bytes(x):
    if type(x) is str:
        return x.encode("utf-8")
    else:
        return x


def from_bytes(x):
    if type(x) is bytes:
        return str(x, "utf-8")
    else:
        return x


class FIFO(object):
    def avail(self, timeout):
        raise NotImplemented()

    def read(self, amount):
        raise NotImplemented()

    def write(self, data):
        raise NotImplemented()

    def openRead(self):
        raise NotImplemented()

    def openWrite(self):
        raise NotImplemented()

    def close(self):
        raise NotImplemented()

    def flush(self):
        raise NotImplemented()


class WindowsFIFO(FIFO):
    pass
    # Removed - didn't work. For now, TCP is used on Windows.


class TCPIO(FIFO):
    sock = None
    sockfile = None
    srvsock = None

    def connect(self, host, port):
        # Attempt an IPV6 socket first
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.connect((host, port))
        except:
            # try an IPV4 socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))

        self.sock = sock
        self.sockfile = sock.makefile("rwb")

    def startServer(self):
        self.srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srvsock.bind(("localhost", 0))
        _, port = self.srvsock.getsockname()
        self.srvsock.listen(1)
        return port

    def acceptConnection(self):
        self.sock, _ = self.srvsock.accept()
        self.sockfile = self.sock.makefile("rwb")

    def avail(self, timeout):
        return bool(select.select([self.sock], [], [], timeout)[0])

    def read(self, amount):
        return self.sockfile.read(amount)

    def write(self, data):
        return self.sockfile.write(data)

    def close(self):
        if self.sock is None or self.sockfile is None:
            return
        self.sockfile.close()
        self.sockfile = self.sock = None

    def flush(self):
        self.sockfile.flush()


class UnixFIFO(FIFO):
    fileobj = None
    name = None
    mode = None

    def __init__(self, name=None):
        if name == None:
            # make one
            name = tempfile.mktemp()
            os.mkfifo(name, 0o600)

        self.name = name

    def avail(self, timeout):
        return bool(select.select([self.fileobj], [], [], timeout)[0])

    def read(self, amount):
        inp = self.fileobj.read(amount)

        # this is necessary in Python 2 for some reason
        if len(inp) == 0:
            # eof? shouldn't happen, reopen the file
            self.fileobj = open(self.name, self.mode)
            inp = self.read(amount)

        return inp

    def write(self, data):
        self.fileobj.write(data)

    def openRead(self):
        self.mode = "rb"
        self.fileobj = open(self.name, self.mode)

    def openWrite(self):
        self.mode = "wb"
        self.fileobj = open(self.name, self.mode)

    def close(self):
        if not self.fileobj is None:
            self.fileobj.close()
        self.fileobj = None

    def flush(self):
        self.fileobj.flush()

    def __del__(self):
        self.close()


if os.name == "nt" or "CYGWIN" in platform.system():
    FIFO = WindowsFIFO
elif os.name == "posix":
    FIFO = UnixFIFO
else:
    raise RuntimeError("unsupported OS")
