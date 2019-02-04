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

# add '' near the front of sys.path so users can import stuff from the
# current directory, just like in a normal interactive python session
sys.path.insert(1,'')

# make sure to load the module this file is actually located in 
mypath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1,mypath)

from pynapl import APLPyConnect as C
from pynapl import IPC

def runSlave(inp,outp):
    print("Opening input file...")

    # Open the input first, then the output. APL does it in the same order
    # (i.e., it opens its output first, which is Python's input). If it is
    # done the other way around, it will block.
    
    if inp=='TCP':
        # then 'outp' is a port number 
        # connect to it
        sock = IPC.TCPIO()
        sock.connect('localhost', int(outp))
        
        conn = C.Connection(sock,sock) 
        
    else:
        inp = IPC.FIFO(inp)
        inp.openRead()

        outp = IPC.FIFO(outp)
        outp.openWrite()

        conn = C.Connection(inp,outp)
   
    print("Connected.")

    conn.runUntilStop()
    sys.exit(0)

if __name__=="__main__":
    
    # if there is '--' in the argument list, drop all arguments before
    if '--' in sys.argv:
        sys.argv = sys.argv[sys.argv.index('--'):]

    infile = sys.argv[1]
    outfile = sys.argv[2]

    if hasattr(os, 'setpgrp'): os.setpgrp()
    signal.signal(signal.SIGINT, signal.default_int_handler)

    if 'thread' in sys.argv:
        print("Starting thread")
        # run in a thread
        threading.Thread(target=lambda:runSlave(infile,outfile)).start()
    else:
        # run normally
        runSlave(infile,outfile)

