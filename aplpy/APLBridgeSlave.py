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

# make sure to load the module this file is actually located in 
mypath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1,mypath)

from aplpy import APLPyConnect as C

if __name__=="__main__":
    
    port = int(sys.argv[1])

    if hasattr(os, 'setpgrp'): os.setpgrp()
    signal.signal(signal.SIGINT, signal.default_int_handler)

    print("Connecting to APL at port %d" % port)
    
	# Attempt an IPV6 socket first 
    try:
        sock = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
        sock.connect(('localhost',port))
    except:
        # try an IPV4 socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost',port))
		
    conn = C.Connection(sock)
    conn.runUntilStop()

    sock.close()
    
