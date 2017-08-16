# IPC

# On Linux, this is implemented with mkfifo
# On Windows, we use named pipes

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import sys, os, tempfile, select, ctypes, socket, platform

from subprocess import Popen, PIPE
from ctypes import * 

# use Python 3 types on Python 2
if sys.version_info.major == 2:
    bytes, str = str, unicode 
 
# convert to bytes
def to_bytes(x):
    if type(x) is str:
        return x.encode('utf-8')
    else:
        return x

def from_bytes(x):
    if type(x) is bytes:
        return str(x, 'utf-8')
    else:
        return x

class FIFO(object):
    def avail(self,timeout): raise NotImplemented()
    def read(self,amount): raise NotImplemented()
    def write(self,data): raise NotImplemented()
    def openRead(self): raise NotImplemented()
    def openWrite(self): raise NotImplemented()
    def close(self): raise NotImplemented()
    def flush(self): raise NotImplemented()
        
 
kernel32 = rpcrt4 = None
def import_windows_functions():
    """Import the necessary Windows functions"""
    global kernel32
    global rpcrt4
    
    if (not kernel32 is None) and (not rpcrt4 is None):
        return # already loaded 
        
    try:
        kernel32 = windll.kernel32
        rpcrt4 = windll.rpcrt4
    except NameError:    
        # Cygwin needs to load them by hand
        winpath = to_bytes(os.environ['WINDIR'])
        kernel32p = winpath+br'\System32\Kernel32.dll'
        rpcrt4p = winpath+br'\System32\Rpcrt4.dll'
        
        # Shell out to convert the paths 
        kernel32cp = Popen([b'cygpath',b'--unix',kernel32p],
                        stdout=PIPE).communicate()[0].split(b"\n")[0]
        rpcrt4cp = Popen([b'cygpath',b'--unix',rpcrt4p],
                        stdout=PIPE).communicate()[0].split(b"\n")[0]
                       
        if sys.version_info.major >= 3:
            kernel32cp = from_bytes(kernel32cp)
            rpcrt4cp = from_bytes(rpcrt4cp)
            
        kernel32 = cdll.LoadLibrary(kernel32cp)
        rpcrt4 = cdll.LoadLibrary(rpcrt4cp)
        
class WindowsFIFO(FIFO):
    handle = None

    name = None
    mode = None
    create_new = False
    
    NAME_PFX = r'\\.\pipe\PYAPL-'
    
    GENERIC_WRITE         = 0x40000000
    GENERIC_READ          = 0x80000000
    CREATE_NEW            = 1
    OPEN_EXISTING         = 3
    FILE_ATTRIBUTE_NORMAL = 128
    PIPE_ACCESS_DUPLEX    = 3
    PIPE_ACCESS_INBOUND   = 1
    PIPE_ACCESS_OUTBOUND  = 2
    PIPE_TYPE_BYTE        = 0
    
    
    def __init__(self, name=None):
        import_windows_functions() 
        
        if name==None:
            n = c_ulong()
            rpcrt4.UuidCreate(byref(n))
            name = WindowsFIFO.NAME_PFX + str(n.value)
            self.create_new = True
        else:
            self.create_new = False 
            
        self.name = name 
        self.dummybuf = create_string_buffer(2)
        self.dummydword = c_ulong()

    def avail(self, timeout):
        # no timeout on Windows (yet? maybe wait?)
        avl = c_ulong()
        b = kernel32.PeekNamedPipe(self.handle,
            self.dummybuf, 1, byref(self.dummydword),
            byref(avl), None)
        return avl.value
        
    
    def _new(self, mode):
        self.handle = kernel32.CreateNamedPipeW(self.name, mode, 
                    0, 255, 1024, 1024, 0, 0)
        if self.handle==-1:
            raise RuntimeError("Cannot create pipe.")

    def _open(self, mode):
        self.handle = kernel32.CreateFileW(self.name, mode, 
                    3, None, self.OPEN_EXISTING, self.FILE_ATTRIBUTE_NORMAL,
                    None)
        if self.handle==-1:
            raise RuntimeError("Cannot open pipe.")
            
    def openRead(self):
        if self.create_new:
            self._new(self.PIPE_ACCESS_INBOUND)
        else:
            self._open(self.GENERIC_READ)
            
    def openWrite(self):
        if self.create_new:
            self._new(self.PIPE_ACCESS_OUTBOUND)
        else: 
            self._open(self.GENERIC_WRITE)
    
    def write(self, data):
        amt = c_ulong()
        s = kernel32.WriteFile(self.handle, c_char_p(data),
                        len(data), byref(amt), None)
        if not s or len(data) != amt.value:
            raise RuntimeError("Write error to pipe.")

    def read(self, size):
        amt = c_ulong()
        buf = create_string_buffer(size)
        s = kernel32.ReadFile(self.handle, buf, size,
                byref(amt), None)
        if not s or size != amt.value: 
            raise RuntimeError("Read error.")
            
        return buf.raw 
    
    def close(self):
        if self.handle and self.handle>0:
            kernel32.CloseHandle(self.handle)
            self.handle=None
    
    def flush(self):
        pass # not buffered it seems on Windows
    
    def __del__(self): self.close() 
    
class TCPIO(FIFO):
    sock=None
    sockfile=None 
    srvsock=None 
    
    def connect(self,host,port):
        # Attempt an IPV6 socket first
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.connect((host,port))
        except:
            # try an IPV4 socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host,port))        
        
        self.sock = sock
        self.sockfile = sock.makefile('rwb')
    
    def startServer(self):
        self.srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srvsock.bind(('localhost', 0))
        _, port = self.srvsock.getsockname()
        self.srvsock.listen(1)
        return port 
        
    def acceptConnection(self): 
        self.sock, _ = self.srvsock.accept()
        self.sockfile = self.sock.makefile('rwb') 
        
    def avail(self,timeout):
        return bool(select.select([self.sock], [], [], timeout)[0])
    
    def read(self,amount):
        return self.sockfile.read(amount) 
        
    def write(self,data):
        return self.sockfile.write(data)
    
    def close(self):
        if self.sock is None or self.sockfile is None: return
        self.sockfile.close()
        self.sockfile=self.sock=None 
        
    def flush(self):
        self.sockfile.flush() 
        
class UnixFIFO(FIFO):
    fileobj = None
    name = None
    mode = None

    def __init__(self, name=None):
        if name==None:
            # make one
            name = tempfile.mktemp()
            os.mkfifo(name, 0o600)

        self.name=name

    def avail(self,timeout):
        return bool(select.select([self.fileobj], [], [], timeout)[0])

    def read(self, amount):
        inp = self.fileobj.read(amount)

        # this is necessary in Python 2 for some reason
        if len(inp)==0:
            # eof? shouldn't happen, reopen the file
            self.fileobj = open(self.name, self.mode)
            inp = self.read(amount)

        return inp

    def write(self, data):
        self.fileobj.write(data)

    def openRead(self):
        self.mode = 'rb'
        self.fileobj = open(self.name, self.mode)

    def openWrite(self):
        self.mode = 'wb'
        self.fileobj = open(self.name, self.mode)

    def close(self):
        if not self.fileobj is None:
            self.fileobj.close()
        self.fileobj = None
    
    def flush(self):
        self.fileobj.flush()

    def __del__(self):
        self.close()



if os.name=='nt' or 'CYGWIN' in platform.system():
    FIFO = WindowsFIFO 
elif os.name=='posix':
    FIFO = UnixFIFO
else:
    raise RuntimeError('unsupported OS')
    

