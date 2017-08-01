#!/usr/bin/env python

# This program will connect to the APL side,
# after which it will execute commands given to it.

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import socket
import sys
import os
import signal
import threading

# make sure to load the module this file is actually located in 
mypath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1,mypath)

from aplpy import APLPyConnect as C

def runSlave(port):
    print("Connecting to APL at port %d" % port)

    # Attempt an IPV6 socket first
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.connect(('localhost',port))
    except:
        # try an IPV4 socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost',port))

    conn = C.Connection(sock)
    conn.runUntilStop()
    sock.close()
    sys.exit(0)

if __name__=="__main__":
    
    # if there is '--' in the argument list, drop all arguments before
    if '--' in sys.argv:
        sys.argv = sys.argv[sys.argv.index('--'):]

    port = int(sys.argv[1])

    if hasattr(os, 'setpgrp'): os.setpgrp()
    signal.signal(signal.SIGINT, signal.default_int_handler)

    if 'thread' in sys.argv:
        # run in a thread
        threading.Thread(target=lambda:runSlave(port)).start()
    else:
        # run normally
        runSlave(port)

