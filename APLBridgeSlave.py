#!/usr/bin/env python

# This program will listen for a connection from the APL side,
# after which it will execute commands given to it.
# It is meant to only take one connection.

import SocketServer
import socket
import threading
import os
import sys

HOST="localhost"
PORT=2526

# message types
class MessageType:
    PID=1      # initial message containing PID 
    STOP=2     # break the connection
    REPR=3     # evaluate Python expr, return repr (for debug)
    

    DBG=254    # print message on stdout and send it back
    ERR=255    # command execution failure
    

class MalformedMessage(Exception): pass


def sendMessage(sockfile, mtype, mdata):
    b4 = (len(mdata) & 0xFF000000) >> 24
    b3 = (len(mdata) & 0x00FF0000) >> 16
    b2 = (len(mdata) & 0x0000FF00) >> 8
    b1 = (len(mdata) & 0x000000FF) >> 0
    sockfile.write("%c%c%c%c%c%s" % (mtype,b4,b3,b2,b1,mdata))
    sockfile.flush()
        
def readMessage(sockfile):
    print "Reading message ",
    # read the header
    try:
        print "header ", 
        mtype = ord(sockfile.read(1))
        lfield = map(ord, sockfile.read(4))
        length = (lfield[0]<<24) + (lfield[1]<<16) + (lfield[2]<<8) + lfield[3]
        print (mtype,lfield,length)
    except (TypeError, IndexError, ValueError):
        # malformed header
        raise MalformedMessage("connection broke while reading message header")

    # read the data
    try:
        print "data",
        data = sockfile.read(length)
    except ValueError:
        raise MalformedMessage("connection broke while reading data")

    if len(data) != length:
        raise MalformedMessage("not enough data available to match message header")

    print "done.\nReceived: ", (mtype, data)
    return (mtype, data)


def handleMessages(sockfile):
    # handle messages in a loop
    stop=False
    while not stop:
        try:
            mtype, data = readMessage(sockfile)
            if mtype==MessageType.STOP:
                print "STOP"
                sendMessage(sockfile, MessageType.STOP, "")
                stop=True
            elif mtype==MessageType.REPR:
                print "REPR ",data
                
                try:
                    val = repr(eval(data))
                    sendMessage(sockfile, MessageType.REPR, val)
                except Exception, e:
                    sendMessage(sockfile, MessageType.ERR, "Python error: "+repr(e))
                
            else:
                print "???"
                sendMessage(sockfile, MessageType.ERR, "invalid mtype %d" % mtype)

        except MalformedMessage, mm:
            print "Error: ", repr(mm)
            sendMessage(sockfile, MessageType.ERR, repr(mm))
            stop=True

def handle(sock):
    pid=os.getpid()

    sockfile = sock.makefile()
    print "Connection established - %d" % pid
        
    sendMessage(sockfile, MessageType.PID,str(pid))
    handleMessages(sockfile)

    sock.close()

if __name__=="__main__":
    port = int(sys.argv[1])

    print "Connecting to APL at port %d" % port
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.connect(('localhost',port))

    handle(sock)
    
