# IPC

# On Linux, this is implemented with mkfifo

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import sys, os, tempfile, select

class FIFO(object):
    def avail(self,timeout): raise NotImplemented()
    def read(self,amount): raise NotImplemented()
    def write(self,data): raise NotImplemented()
    def openRead(self): raise NotImplemented()
    def openWrite(self): raise NotImplemented()
    def close(self): raise NotImplemented()
    def flush(self): raise NotImplemented()
        
class UnixFIFO(FIFO):
    fileobj = None
    name = None

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
        if sys.version_info.major==2 and inp=='':
            self.fileobj.seek(0)
            inp = self.fileobj.read(amount)

        return inp

    def write(self, data):
        self.fileobj.write(data)

    def openRead(self):
        self.fileobj = open(self.name,'rb')

    def openWrite(self):
        self.fileobj = open(self.name,'wb')

    def close(self):
        if not self.fileobj is None:
            self.fileobj.close()
        self.fileobj = None
    
    def flush(self):
        self.fileobj.flush()

    def __del__(self):
        self.close()



if os.name == 'posix':
    FIFO = UnixFIFO 

