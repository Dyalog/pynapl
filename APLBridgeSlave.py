#!/usr/bin/env python

# This program will listen for a connection from the APL side,
# after which it will execute commands given to it.
# It is meant to only take one connection.

import socket
import sys
import APLPyConnect as C

if __name__=="__main__":
    port = int(sys.argv[1])

    print "Connecting to APL at port %d" % port
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.connect(('localhost',port))

    conn = C.Connection(sock)
    conn.runUntilStop()

    sock.close()
    
