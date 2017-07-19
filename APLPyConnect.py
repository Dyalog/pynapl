# APLPyConnect

# This module handles the passing of messages between the APL side and the Python side

# The format of a message is:
#   0     1  2  3  4         ......
#   TYPE  SIZE (big-endian)  MESSAGE (`size` bytes, expected to be UTF-8 encoded)

import socket, os
import Array

class Message(object):
    """A message to be sent to the other side"""
    
    OK=0       # sent as response to message that succeeded but returns nothing
    PID=1      # initial message containing PID 
    STOP=2     # break the connection
    REPR=3     # evaluate expr, return repr (for debug)
    EXEC=4     # execute statement(s), return OK or ERR

    
    DBGSerializationRoundTrip = 253 # 
    DBG=254    # print message on stdout and send it back
    ERR=255    # Python error

    MAX_LEN = 2**32-1

    def __init__(self, mtype, mdata):
        """Initialize a message"""
        self.type = mtype
        self.data = mdata
        if type(self.data) is unicode: 
            self.data = self.data.encode("utf8")
        if len(self.data) > Message.MAX_LEN:
            raise ValueError("message body exceeds maximum length")


    def send(self, writer):
        """Send a message using a writer"""
        b4 = (len(self.data) & 0xFF000000) >> 24
        b3 = (len(self.data) & 0x00FF0000) >> 16
        b2 = (len(self.data) & 0x0000FF00) >> 8
        b1 = (len(self.data) & 0x000000FF) >> 0
        writer.write("%c%c%c%c%c%s" % (self.type,b4,b3,b2,b1,self.data))
        writer.flush()

    @staticmethod
    def recv(reader):
        """Read a message from a reader"""

        # read the header
        try:
            mtype = ord(reader.read(1))
            lfield = map(ord, reader.read(4))
            length = (lfield[0]<<24) + (lfield[1]<<16) + (lfield[2]<<8) + lfield[3]
        except (TypeError, IndexError, ValueError):
            raise MalformedMessage("out of data while reading message header")

        # read the data
        try:
            data = reader.read(length)
        except ValueError:
            raise MalformedMessage("out of data while reading message body")

        if len(data) != length:
            raise MalformedMessage("out of data while reading message body")

        return Message(mtype, data)


class Connection(object):
    """A connection"""
        
    def __init__(self, socket, signon=True):
        self.socket = socket
        self.sockfile = socket.makefile()
        if signon:
            Message(Message.PID, str(os.getpid())).send(self.sockfile)

    def runUntilStop(self):
        """Receive messages and respond to them until STOP is received"""
        self.stop = False
        while not self.stop:
            self.respond(Message.recv(self.sockfile))

    def respond(self, message):
        """Respond to a message"""
        
        t = message.type
        if t==Message.OK:
            # return 'OK' to such messages
            Message(Message.OK, message.data).send(self.sockfile)

        elif t==Message.PID:
            # this is interpreted as asking for the PID
            Message(Message.PID, str(os.getpid())).send(self.sockfile)
        
        elif t==Message.STOP:
            # send a 'STOP' back in acknowledgement and set the stop flag
            self.stop = True
            Message(Message.STOP, "STOP").send(self.sockfile)
        
        elif t==Message.REPR:
            # evaluate the input and send the Python representation back
            try:
                val = repr(eval(message.data))
                Message(Message.REPR, val).send(self.sockfile)
            except Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)

        elif t==Message.EXEC:
            # execute some Python code in the global context
            try:
                code = compile(message.data, '<APL>', 'exec')
                exec code in globals()
                Message(Message.OK, '').send(self.sockfile)
            except Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)


        elif t==Message.DBGSerializationRoundTrip:
            # this is a debug message. Deserialize the contents, print them to stdout, reserialize and send back
            try:
                print "Received data: ", message.data
                print "---------------"

                aplarr = Array.APLArray.fromJSONString(message.data)
                serialized = aplarr.toJSONString()

                print "Sending back: ", serialized
                print "---------------"

                Message(Message.DBGSerializationRoundTrip, serialized).send(self.sockfile)
            except IndexError, e: #Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)
        else:
            Message(Message.ERR, "unknown message type #%d"%message.type).send(self.sockfile)

