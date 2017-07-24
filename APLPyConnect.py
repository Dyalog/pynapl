# APLPyConnect
# -*- coding: utf-8 -*-

# This module handles the passing of messages between the APL side and the Python side

# The format of a message is:
#   0     1  2  3  4         ......
#   TYPE  SIZE (big-endian)  MESSAGE (`size` bytes, expected to be UTF-8 encoded)

import socket, os, time
import RunDyalog
from Array import *

class APLError(Exception): pass
class MalformedMessage(Exception): pass

class Message(object):
    """A message to be sent to the other side"""
    
    OK=0       # sent as response to message that succeeded but returns nothing
    PID=1      # initial message containing PID 
    STOP=2     # break the connection
    REPR=3     # evaluate expr, return repr (for debug)
    EXEC=4     # execute statement(s), return OK or ERR
    REPRRET=5  # return from "REPR"
    
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

    def __init__(self, expr, args, conn):
        self.args=args
        self.pyargs=[]
        self.expr=expr
        self.conn=conn
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
            raise TypeError("expression argument length mismatch")

            

    def go(self):
        local = {'args':self.pyargs, 'retval':None, 'code':self.expr, 'APL':self.conn.apl}
        exec self.wrapper in globals(), local
        retval = local['retval']
        if not isinstance(retval, APLArray):
            retval = APLArray.from_python(retval)

        return retval 
        

class Connection(object):
    """A connection"""
    
    pid=None

    class APL(object):
        """Represents the APL interpreter."""
        def __init__(self, conn):
            self.conn=conn

        def stop(self):
            """If the connection was initiated from the Python side, this will close it."""
            if not self.pid is None:
                # already killed it? (destructor might call this function after the user has called it as well)
                if self.pid == 0: 
                    return
                Message(Message.STOP, "STOP").send(self.conn.sockfile)
                # give the APL process half a second to exit cleanly
                time.sleep(.5)
                try: os.kill(self.pid, 15) # SIGTERM
                except OSError: pass # just leak the instance, it will be cleaned up once Python exits
                self.pid=0
            else: 
                raise ValueError("Connection was not started from the Python end.")

        def __del__(self):
            if self.pid: self.stop()

        def fn(self, aplfn, raw=False):
            """Expose an APL function to Python.

            The result will be considered niladic if called with no arguments,
            monadic if called with one and dyadic if called with two.
            
            If "raw" is set, the return value will be given as an APLArray rather
            than be converted to a 'suitable' Python representation.
            """

            def __fn(*args):
                if len(args)==0: return self.eval(aplfn)
                if len(args)==1: return self.eval("(%s)⊃∆"%aplfn, args[0])
                if len(args)==2: return self.eval("(⊃∆)(%s)2⊃∆"%aplfn, args[0], args[1])
                return APLError("Function must be niladic, monadic or dyadic.")

            return __fn

        def repr(self, aplcode):
            """Run an APL expression, return string representation"""
            
            # send APL message
            Message(Message.REPR, aplcode).send(self.conn.sockfile)
            reply = self.conn.expect(Message.REPRRET)

            if reply.type == Message.ERR:
                raise APLError(reply.data)
            else:
                return reply.data

        def fix(self, code):
            """2⎕FIX an APL script. It will become available in the workspace.
               Input may be a string or a list."""

            # implemented using eval 

            if type(code) in (str,unicode):
                code = code.split("\n") # luckily APL has no multiline strings
            
            return self.eval("2⎕FIX ∆", *code)
                
        def eval(self, aplexpr, *args, **kwargs):
            """Evaluate an APL expression. Any extra arguments will be exposed
               as an array ∆. If `raw' is set, the result is not converted to a
               Python representation."""
           
            if not type(aplexpr) is unicode:
                # this should be an UTF-8 string
                aplexpr=unicode(aplexpr, "utf8")

            payload = APLArray.from_python([aplexpr, args]).toJSONString()
            Message(Message.EVAL, payload).send(self.conn.sockfile)

            reply = self.conn.expect(Message.EVALRET)

            if reply.type == Message.ERR:
                raise APLError(reply.data)

            answer = APLArray.fromJSONString(reply.data)

            if 'raw' in kwargs and kwargs['raw']:
                return answer
            else:
                return answer.to_python()

    @staticmethod
    def APLClient(DEBUG=False):
        """Start an APL client. This function returns an APL instance."""
        
        # start a server
        srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srvsock.bind(('localhost', 0))
        _, port = srvsock.getsockname()

        if DEBUG:print "Waiting for connection at %d" % port
        srvsock.listen(1)
        
        if not DEBUG: RunDyalog.dystart(port)

        conn, _ = srvsock.accept()

        if DEBUG:print "Waiting for PID..."
        connobj = Connection(conn, signon=False)

        # ask for the PID
        pidmsg = connobj.expect(Message.PID)
        
        if pidmsg.type==Message.ERR:
            raise APLError(pidmsg.data)
        else:
            pid=int(pidmsg.data)
            if DEBUG:print "Ok! pid=%d" % pid
            apl = connobj.apl
            apl.pid = pid
            return apl

    def __init__(self, socket, signon=True):
        self.socket = socket
        self.sockfile = socket.makefile()
        self.apl = Connection.APL(self)
        if signon:
            Message(Message.PID, str(os.getpid())).send(self.sockfile)

    def runUntilStop(self):
        """Receive messages and respond to them until STOP is received"""
        self.stop = False
        while not self.stop:
            self.respond(Message.recv(self.sockfile))

    def expect(self, msgtype):
        """Expect a certain type of message. If such a message or an error
           is received, return it; if a different message is received, then
           handle it and go back to waiting for the right type of message."""

        while True:
            msg = Message.recv(self.sockfile)

            if msg.type in (msgtype, Message.ERR):
                return msg
            else:
                self.respond(msg)


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
                Message(Message.REPRRET, val).send(self.sockfile)
            except Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)

        elif t==Message.EXEC:
            # execute some Python code in the global context
            try:
                code = compile(message.data, '<APL>', 'exec')
                globals()['APL']=self.apl
                exec code in globals()
                Message(Message.OK, '').send(self.sockfile)
            except Exception, e:
                Message(Message.ERR, repr(e)).send(self.sockfile)


        elif t==Message.EVAL:
            # evaluate a Python expression with optional arguments
            # expected input: APLArray, first elem = expr string, 2nd elem = arguments
            # output, if not an APLArray already, will be automagically converted

            try:
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

                result = PyEvaluator(code, args, self).go().toJSONString()
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
            Message(Message.ERR, "unknown message type #%d / data:%s"%(message.type,message.data)).send(self.sockfile)

