# APLPyConnect
# -*- coding: utf-8 -*-

# This module handles the passing of messages between the APL side and the Python side

# The format of a message is:
#   0     1  2  3  4         ......
#   TYPE  SIZE (big-endian)  MESSAGE (`size` bytes, expected to be UTF-8 encoded)

import socket, os, time, types, signal, threading, select
import RunDyalog, Interrupt, WinDyalog
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

        # turn off interrupt signal handler temporarily
        s = signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            b4 = (len(self.data) & 0xFF000000) >> 24
            b3 = (len(self.data) & 0x00FF0000) >> 16
            b2 = (len(self.data) & 0x0000FF00) >> 8
            b1 = (len(self.data) & 0x000000FF) >> 0
            writer.write("%c%c%c%c%c%s" % (self.type,b4,b3,b2,b1,self.data))
            writer.flush()
        finally:
            signal.signal(signal.SIGINT, s) 

    @staticmethod
    def recv(reader):
        """Read a message from a reader"""

        s = None
        setsgn = False
        
        try:
            # wait for message available
            while True:
                ready = select.select([reader], [], [], 0.5)
                if ready[0]: break
            
            # read the header
            try:
                mtype = ord(reader.read(1))
                # once we've started reading, finish reading: turn off the interrupt handler
                setsgn, s = True, signal.signal(signal.SIGINT, signal.SIG_IGN)

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
        finally:
            # turn the interrupt handler back on if we'd turned it off
            if setsgn:
                signal.signal(signal.SIGINT, s)

class PyEvaluator(object):
    """Evaluate a Python expression"""

    # If it's stupid and it works, it's still stupid, but at least it works
    wrapper=compile("retval = eval(code)",'<APL>','exec')

    def __init__(self, expr, args, conn):
        self.args=args
        self.pyargs=[]
        self.expr=expr
        self.conn=conn
        self.__expr_arg_subst()
        self.__check_arg_lens_match()

    def __expr_arg_subst(self):
        narg = 0
        build = []
        inString = False
        sDelim = ""
        escape = False

        i=0
        while i < len(self.expr):
           
            # if this character is escaped, skip it
            if escape:
                escape=False
                build.append(self.expr[i])
                i+=1
                continue

            
            # if \ in a string, the next character is excaped
            if inString and self.expr[i] == '\\':
                escape=True
                build.append(self.expr[i])
                i+=1
                continue

            # if in a string, check if this is the delimiter
            if inString:
                if self.expr[i:i+len(sDelim)]==sDelim:
                    # this is the end of the string
                    inString=False
                    build.append(self.expr[i:i+len(sDelim)])
                    i+=len(sDelim)
                else:
                    # keep searching
                    build.append(self.expr[i])
                    i+=1
                continue

            # if not in a string, check if this is the start of a multiline string
            if self.expr[i:i+3] in ("'''", '"""'):
                # multiline string
                sDelim = self.expr[i:i+3]
                inString = True
                build.append(self.expr[i:i+3])
                i+=3
                continue

            # single-line string
            if self.expr[i] in '\'"':
                sDelim = self.expr[i]
                inString = True
                build.append(self.expr[i])
                i+=1
                continue

            # if it's not any 
            ch=self.expr[i]
            if ch in u'⎕⍞':
                build.append('args[%d]' % narg)
                curarg = self.args[[narg]]
                if ch==u'⎕' and (isinstance(curarg,APLArray) or isinstance(curarg,APLNamespace)):
                    # this argument should be converted to a suitable Python representation
                    self.pyargs.append(curarg.to_python())
                else:
                    self.pyargs.append(curarg)
                    
                narg+=1
            else:
                build.append(ch)
            i+=1

        self.expr=compile(''.join(build), '<APL>', 'eval')

    def __check_arg_lens_match(self):
        if self.args.rho[0] != len(self.pyargs):
        #if self.args.rho[0] != sum(ch in u"⎕⍞" for ch in self.expr):
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

    
    #pid=None

    class APL(object):
        pid=None

        """Represents the APL interpreter."""
        def __init__(self, conn):
            self.conn=conn
            self.ops=0 # keeps track of how many operators have been defined

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

            if not type(aplfn) is unicode:
                aplfn = unicode(aplfn, "utf-8")

            def __fn(*args):
                if len(args)==0: return self.eval(aplfn, raw=raw)
                if len(args)==1: return self.eval(u"(%s)⊃∆"%aplfn, args[0], raw=raw)
                if len(args)==2: return self.eval(u"(⊃∆)(%s)2⊃∆"%aplfn, args[0], args[1], raw=raw)
                return APLError("Function must be niladic, monadic or dyadic.")

            # op can use this for an optimization
            __fn.aplfn = aplfn

            return __fn

        def op(self, aplop):
            """Expose an APL operator.

            It can be called with either 1 or 2 arguments, depending on whether the
            operator is monadic or dyadic. The arguments may be values or Python
            functions.

            If the Python function was created using apl.fn, this is recognized
            and the function is run in APL directly.
            """

            if not type(aplop) is unicode:
                aplop = unicode(aplop, "utf-8")

            def storeArgInWs(arg,nm):
                wsname = u"___op%d_%s" % (self.ops, nm)

                if type(arg) is types.FunctionType \
                or type(arg) is types.BuiltinFunctionType:
                    # it is a function
                    if hasattr(arg,'__dict__') and 'aplfn' in arg.__dict__:
                        # it is an APL function
                        self.eval(u"%s ← %s⋄⍬" % (wsname, arg.aplfn))
                    else:
                        # it is a Python function
                        # store it under this name
                        self.__dict__[wsname] = arg
                        # make it available to APL
                        self.eval(u"%s ← (py.PyFn'APL.%s').Call⋄⍬" % (wsname, wsname))
                else:
                    # it is a value
                    self.eval(u"%s ← ⊃∆⋄⍬" % wsname, arg) 
                return wsname

            def __op(aa, ww=None, raw=False):
               

                # store the arguments into APL at the time that the operator is defined
                wsaa = storeArgInWs(aa, "aa")
               
                aplfn = u"((%s)(%s))" % (wsaa, aplop)

                # . / ∘. must be special-cased
                if aplop in [u".",u"∘."]: aplfn=u'(∘.(%s))' % wsaa

                if not ww is None: 
                    wsww = storeArgInWs(ww, "ww")
                    aplfn = u"((%s)%s(%s))" % (wsaa, aplop, wsww)
                    # again, . / ∘. must be special-cased
                    if aplop in [u".",u"∘."]: aplfn=u'((%s).(%s))' % (wsaa, wsww)
                
                def __fn(*args):
                    # an APL operator can't return a niladic function
                    if len(args)==0: raise APLError("A function derived from an APL operator cannot be niladic.")
                    if len(args)==1: return self.eval(u"(%s)⊃∆"%aplfn, args[0], raw=raw)
                    if len(args)==2: return self.eval(u"(⊃∆)(%s)2⊃∆"%aplfn, args[0], args[1], raw=raw)
                    raise APLError("Function must be monadic or dyadic.")

                __fn.aplfn = aplfn
                self.ops+=1
                return __fn
            

            return __op

        def interrupt(self):
            """Send a strong interrupt to the Dyalog interpreter."""
            # TODO: windows support?
            if self.pid:
                #os.kill(self.pid, signal.SIGINT)
				Interrupt.interrupt(self.pid)

        def tradfn(self, tradfn):
            """Define a tradfn or tradop on the APL side.

            Input must be string, the lines of which will be passed to ⎕FX."""

            Message(Message.EXEC, tradfn).send(self.conn.sockfile)
            reply = self.conn.expect(Message.OK)

            if reply.type == Message.ERR:
                raise APLError(reply.data)
            else:
                return self.fn(reply.data)

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

            # normalize (remove superfluous whitespace and newlines, add in ⋄s where
            # necessary)

            aplexpr = u'⋄'.join(x.strip() for x in aplexpr.split(u"\n") if x.strip()) \
                          .replace(u'{⋄',u'{').replace(u'⋄}',u'}') \
                          .replace(u'(⋄',u'(').replace(u'⋄)',u')')

            # print "evaluating: ", aplexpr

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
    def APLClient(DEBUG=False, dyalog=None):
        """Start an APL client. This function returns an APL instance."""
        
        # start a server
        srvsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srvsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srvsock.bind(('localhost', 0))
        _, port = srvsock.getsockname()

        if DEBUG:print "Waiting for connection at %d" % port
        srvsock.listen(1)
        
        if not DEBUG: RunDyalog.dystart(port, dyalog=dyalog)

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
            
            # if we are on Windows, hide the window
            if os.name=='nt': WinDyalog.hide(pid)
            
            return apl

    def __init__(self, socket, signon=True):
        self.socket = socket
        self.sockfile = socket.makefile()
        self.apl = Connection.APL(self)
        self.__interrupt_lock = threading.Lock()
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
            try:
                msg = Message.recv(self.sockfile)

                if msg.type in (msgtype, Message.ERR):
                    return msg
                else:
                    self.respond(msg)
            except KeyboardInterrupt:
                self.apl.interrupt()

    def respond(self, message):
        # Add ctrl+c signal handling
        try:
            self.respond_inner(message)
        except KeyboardInterrupt:
            # If there is an interrupt during 'respond', then that means
            # the Python side was interrupted, and we need to tell the
            # APL this.
            Message(Message.ERR, "Interrupt").send(self.sockfile)


    def respond_inner(self, message):
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
                #raise
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

