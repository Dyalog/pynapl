# APLPyConnect
# -*- coding: utf-8 -*-

# This module handles the passing of messages between the APL side and the Python side

# The format of a message is:
#   0     1  2  3  4         ......
#   TYPE  SIZE (big-endian)  MESSAGE (`size` bytes, expected to be UTF-8 encoded)

import socket, os
from Array import *

class APLException(Exception): pass
class MalformedMessage(Exception): pass

class Message(object):
    """A message to be sent to the other side"""
    
    OK=0       # sent as response to message that succeeded but returns nothing
    PID=1      # initial message containing PID 
    STOP=2     # break the connection
    REPR=3     # evaluate expr, return repr (for debug)
    EXEC=4     # execute statement(s), return OK or ERR

    EVAL=10    # evaluate a Python expression, including arguments, with APL conversion
    EVALRET=11 # message containing the result of an evaluation
    
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

class PyEvaluator(object):
    """Evaluate a Python expression"""

    # If it's stupid and it works, it's still stupid, but at least it works
    wrapper=compile("retval = eval(code)",'<APL>','exec')

    def __init__(self, expr, args):
        self.args=args
        self.pyargs=[]
        self.expr=expr
        self.__check_arg_lens_match()
        self.__expr_arg_subst()

    def __expr_arg_subst(self):
        narg = 0
        build = []
        for ch in self.expr:
            if ch in u'⎕⍞':
                build.append('args[%d]' % narg)
                curarg = self.args[[narg]]
                if ch==u'⎕' and isinstance(curarg,APLArray):
                    # this argument should be converted to a suitable Python representation
                    self.pyargs.append(curarg.to_python())
                else:
                    self.pyargs.append(curarg)
                    
                narg+=1
            else:
                build.append(ch)

        self.expr=compile(''.join(build), '<APL>', 'eval')

    def __check_arg_lens_match(self):
        if self.args.rho[0] != sum(ch in u"⎕⍞" for ch in self.expr):
            raise APLException("expression argument length mismatch")

            

    def go(self):
        local = {'args':self.pyargs, 'retval':None, 'code':self.expr}
        exec self.wrapper in globals(), local
        retval = local['retval']
        if not isinstance(retval, APLArray):
            retval = APLArray.from_python(retval)

        return retval 
        

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


        elif t==Message.EVAL:
            # evaluate a Python expression with optional arguments
            # expected input: APLArray, first elem = expr string, 2nd elem = arguments
            # output, if not an APLArray already, will be automagically converted

            try:
                print "received: ", message.data

                val = APLArray.fromJSONString(message.data)
                # unpack code
                if val.rho != [2]: 
                    raise MalformedMessage("EVAL expects a ⍴=2 array, but got: %s" % repr(val.rho))

                if not isinstance(val[[0]], APLArray):
                    raise MalformedMessage("First argument must contain code string.")

                code = val[[0]].to_python()
                if not type(code) in (str,unicode):
                    raise MalformedMessage("Code element must be a string, but got: %s" % repr(code))

                # unpack arguments
                args = val[[1]]
                if not isinstance(val[[1]], APLArray) \
                or len(val[[1]].rho) != 1:
                    raise MalformedMessage("Argument list must be rank-1 array.")

                result = PyEvaluator(code, args).go().toJSONString()
                Message(Message.EVALRET, result).send(self.sockfile)
            except Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)


        elif t==Message.DBGSerializationRoundTrip:
            # this is a debug message. Deserialize the contents, print them to stdout, reserialize and send back
            try:
                print "Received data: ", message.data
                print "---------------"

                aplarr = APLArray.fromJSONString(message.data)
                serialized = aplarr.toJSONString()

                print "Sending back: ", serialized
                print "---------------"

                Message(Message.DBGSerializationRoundTrip, serialized).send(self.sockfile)
            except IndexError, e: #Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)
        else:
            Message(Message.ERR, "unknown message type #%d"%message.type).send(self.sockfile)

