#!/usr/bin/env python

# This program will listen for a connection from the APL side,
# after which it will execute commands given to it.

import SocketServer
import socket
import threading
import os

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

class APLTCPHandler(SocketServer.BaseRequestHandler):
    def sendMessage(self, mtype, mdata):
        b4 = (len(mdata) & 0xFF000000) >> 24
        b3 = (len(mdata) & 0x00FF0000) >> 16
        b2 = (len(mdata) & 0x0000FF00) >> 8
        b1 = (len(mdata) & 0x000000FF) >> 0
        self.request.sendall("%c%c%c%c%c%s" % (mtype,b4,b3,b2,b1,mdata))
        
    def readMessage(self):
        print "Reading message ",
        # read the header
        try:
            print "header ", 
            mtype = ord(self.sockfile.read(1))
            lfield = map(ord, self.sockfile.read(4))
            length = (lfield[0]<<24) + (lfield[1]<<16) + (lfield[2]<<8) + lfield[3]
            print (mtype,lfield,length)
        except (TypeError, IndexError, ValueError):
            # malformed header
            raise MalformedMessage("connection broke while reading message header")

        # read the data
        try:
            print "data",
            data = self.sockfile.read(length)
        except ValueError:
            raise MalformedMessage("connection broke while reading data")

        if len(data) != length:
            raise MalformedMessage("not enough data available to match message header")

        print "done.\nReceived: ", (mtype, data)
        return (mtype, data)


    def handleMessages(self):
        # handle messages in a loop
        stop=False
        while not stop:
            try:
                mtype, data = self.readMessage()

                if mtype==MessageType.STOP:
                    print "STOP"
                    self.sendMessage(MessageType.STOP, "")
                    stop=True
                elif mtype==MessageType.REPR:
                    print "REPR ",data
                    self.sendMessage(MessageType.REPR, repr(eval(data)))
                else:
                    print "???"
                    self.sendMessage(MessageType.ERR, "invalid mtype %d" % mtype)

            except MalformedMessage, mm:
                print "Error: ", repr(mm)
                self.sendMessage(MessageType.ERR, repr(mm))
                stop=True

    def handle(self):
        pid=os.getpid()

        self.sockfile = self.request.makefile()
        print "Connection established - %d" % pid
        
        self.sendMessage(MessageType.PID,str(pid))

        self.handleMessages()

        self.request.close()

class APLTCPServer(SocketServer.ThreadingTCPServer, object):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return super(APLTCPServer, self).server_bind()

if __name__=="__main__":
    server = APLTCPServer((HOST, PORT), APLTCPHandler)
    server.serve_forever()
