#!/usr/bin/env python

# This program will connect to the APL side,
# after which it will execute commands given to it.

import socket
import sys
import os
import signal
import APLPyConnect as C

if __name__=="__main__":
    port = int(sys.argv[1])

    os.setpgrp()
    signal.signal(signal.SIGINT, signal.default_int_handler)

    print "Connecting to APL at port %d" % port
    
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
    
