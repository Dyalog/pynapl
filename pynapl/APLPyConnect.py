# APLPyConnect
# -*- coding: utf-8 -*-

# This module handles the passing of messages between the APL side and the Python side

# The format of a message is:
#   0     1  2  3  4         ......
#   TYPE  SIZE (big-endian)  MESSAGE (`size` bytes, expected to be UTF-8 encoded)


import json
import os
import platform
import signal
import sys
import time
import types

from .Array import *
import Interrupt
import IPC
from .PyEvaluator import PyEvaluator
from .ObjectWrapper import *
import RunDyalog
import WinDyalog


# in Python 2, set string types to be their Python 3 equivalents
if sys.version_info.major == 2:
    bytes, str = str, unicode

# in Python 3, allow use of long
if sys.version_info.major >= 3:
    long = int

# in Python 2, sockets give bytes as ASCII characters.
# in Python 3, sockets give either Unicode or bytes as ints.
def maybe_ord(item):
    if type(item) in (int, long):
        return item
    else:
        return ord(item)


# these fail when threaded, but that's OK
def ignoreInterrupts():
    try:
        return signal.signal(signal.SIGINT, signal.SIG_IGN)
    except ValueError:
        return None  # (not on main thread)


def allowInterrupts():
    try:
        return signal.signal(signal.SIGINT, signal.default_int_handler)
    except ValueError:
        return None  # pass (not on main thread)


def setInterrupts(x):
    if x == None:
        return None
    try:
        return signal.signal(signal.SIGINT, x)
    except ValueError:
        return None  # pass (not on main thread)


class APLError(Exception):
    def __init__(self, message="", jsobj=None):
        self.dmx = None
        # if a JSON object is given, use that
        if not jsobj is None:
            if type(jsobj) is bytes:
                jsobj = str(jsobj, "utf-8")
            errobj = json.loads(jsobj)
            message = errobj["Message"]
            if "DMX" in errobj:
                self.dmx = errobj["DMX"]
                if "Message" in self.dmx and self.dmx["Message"].strip():
                    message += ": " + self.dmx["Message"]

        # if on Python 3 and these are bytes, convert to unicode
        if sys.version_info.major >= 3 and type(message) is bytes:
            Exception.__init__(self, str(message, "utf-8"))
        else:
            Exception.__init__(self, message)


class MalformedMessage(Exception):
    pass


class Message(object):
    """A message to be sent to the other side"""

    OK = 0  # sent as response to message that succeeded but returns nothing
    PID = 1  # initial message containing PID
    STOP = 2  # break the connection
    REPR = 3  # evaluate expr, return repr (for debug)
    EXEC = 4  # execute statement(s), return OK or ERR
    REPRRET = 5  # return from "REPR"

    EVAL = 10  # evaluate a Python expression, including arguments, with APL conversion
    EVALRET = 11  # message containing the result of an evaluation

    DBGSerializationRoundTrip = 253  #
    ERR = 255  # Python error

    MAX_LEN = 2**32 - 1

    def __init__(self, mtype, mdata):
        """Initialize a message"""
        self.type = mtype
        self.data = mdata
        if type(self.data) is str:
            self.data = self.data.encode("utf8")
        if len(self.data) > Message.MAX_LEN:
            raise ValueError("message body exceeds maximum length")

    def send(self, writer):
        """Send a message using a writer"""

        # turn off interrupt signal handler temporarily
        s = None

        # this fails under Python 3 if it happens during shutdown
        # the workaround is to just ignore it in that case
        # the error claims SIG_IGN isn't a valid signal
        try:
            s = signal.signal(signal.SIGINT, signal.SIG_IGN)
        except (TypeError, ValueError):
            pass

        try:
            b4 = (len(self.data) & 0xFF000000) >> 24
            b3 = (len(self.data) & 0x00FF0000) >> 16
            b2 = (len(self.data) & 0x0000FF00) >> 8
            b1 = (len(self.data) & 0x000000FF) >> 0

            # Python 2 and 3 handle this differently
            # Annoyingly enough, the newest Python 3 (.6) has added support for this back in,
            # but we can't expect that version to be present just yet
            if sys.version_info.major == 2:
                writer.write(b"%c%c%c%c%c%s" % (self.type, b4, b3, b2, b1, self.data))
            else:
                writer.write(bytes([self.type, b4, b3, b2, b1]))
                writer.write(self.data)

            writer.flush()
        finally:
            if s:
                signal.signal(signal.SIGINT, s)

    @staticmethod
    def recv(reader, block=True):
        """Read a message from a reader.

        If block is set to False, then it will return None if no message is
        available, rather than wait until one comes in.
        """

        s = None
        setsgn = False

        try:
            if block:
                # wait for message available
                while True:
                    if reader.avail(0.1):
                        break
            else:
                # if no message available, return None
                if not reader.avail(0.1):
                    return None

                # once we've started reading, finish reading: turn off the interrupt handler
            try:
                s, setsgn = signal.signal(signal.SIGINT, signal.SIG_IGN), True
            except ValueError:
                pass  # we're not on the main thread, so no signaling at all

            # read the header
            try:
                inp = reader.read(1)

                mtype = maybe_ord(inp)

                lfield = list(map(maybe_ord, reader.read(4)))
                length = (
                    (lfield[0] << 24) + (lfield[1] << 16) + (lfield[2] << 8) + lfield[3]
                )
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


class Connection(object):
    """A connection"""

    class APL(object):
        """Represents the APL interpreter."""

        pid = None
        DEBUG = False
        store = None

        def __init__(self, conn):
            self.store = ObjectStore()
            self.conn = conn
            self.ops = 0  # keeps track of how many operators have been defined

        def obj(self, obj):
            """Wrap an object so it can be sent to APL."""
            return ObjectWrapper(self.store, obj)

        def _access(self, ref):
            """Called by the APL side to access a Python object"""
            return self.store.retrieve(ref)

        def _release(self, ref):
            """Called by the APL side to release an object it has sent."""
            self.store.release(ref)

        def stop(self):
            """If the connection was initiated from the Python side, this will close it."""
            if not self.pid is None:
                # already killed it? (destructor might call this function after the user has called it as well)
                if not self.pid:
                    return
                try:
                    Message(Message.STOP, "STOP").send(self.conn.outfile)
                except (ValueError, AttributeError):
                    pass  # if already closed, don't care

                # close the pipes
                try:
                    self.conn.infile.close()
                    self.conn.outfile.close()
                except:
                    pass  # we're gone anyway

                # give the APL process half a second to exit cleanly
                time.sleep(0.5)

                if not self.DEBUG:
                    try:
                        os.kill(self.pid, 15)  # SIGTERM
                    except OSError:
                        pass  # just leak the instance, it will be cleaned up once Python exits

                self.pid = 0

            else:
                raise ValueError("Connection was not started from the Python end.")

        def __del__(self):
            if self.pid:
                self.stop()

        def fn(self, aplfn, raw=False):
            """Expose an APL function to Python.

            The result will be considered niladic if called with no arguments,
            monadic if called with one and dyadic if called with two.

            If "raw" is set, the return value will be given as an APLArray rather
            than be converted to a 'suitable' Python representation.
            """

            if not type(aplfn) is str:
                aplfn = str(aplfn, "utf-8")

            def __fn(*args):
                if len(args) == 0:
                    return self.eval(aplfn, raw=raw)
                if len(args) == 1:
                    return self.eval("(%s)⊃∆" % aplfn, args[0], raw=raw)
                if len(args) == 2:
                    return self.eval("(⊃∆)(%s)2⊃∆" % aplfn, args[0], args[1], raw=raw)
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

            if not type(aplop) is str:
                aplop = str(aplop, "utf-8")

            def storeArgInWs(arg, nm):
                wsname = "___op%d_%s" % (self.ops, nm)

                if (
                    type(arg) is types.FunctionType
                    or type(arg) is types.BuiltinFunctionType
                ):
                    # it is a function
                    if hasattr(arg, "__dict__") and "aplfn" in arg.__dict__:
                        # it is an APL function
                        self.eval("%s ← %s⋄⍬" % (wsname, arg.aplfn))
                    else:
                        # it is a Python function
                        # store it under this name
                        self.__dict__[wsname] = arg
                        # make it available to APL
                        self.eval("%s ← (py.PyFn'APL.%s').Call⋄⍬" % (wsname, wsname))
                else:
                    # it is a value
                    self.eval("%s ← ⊃∆" % wsname, arg)
                return wsname

            def __op(aa, ww=None, raw=False):

                # store the arguments into APL at the time that the operator is defined
                wsaa = storeArgInWs(aa, "aa")

                aplfn = "((%s)(%s))" % (wsaa, aplop)

                # . / ∘. must be special-cased
                if aplop in [".", "∘."]:
                    aplfn = "(∘.(%s))" % wsaa

                if not ww is None:
                    wsww = storeArgInWs(ww, "ww")
                    aplfn = "((%s)%s(%s))" % (wsaa, aplop, wsww)
                    # again, . / ∘. must be special-cased
                    if aplop in [".", "∘."]:
                        aplfn = "((%s).(%s))" % (wsaa, wsww)

                def __fn(*args):
                    # an APL operator can't return a niladic function
                    if len(args) == 0:
                        raise APLError(
                            "A function derived from an APL operator cannot be niladic."
                        )
                    if len(args) == 1:
                        return self.eval("(%s)⊃∆" % aplfn, args[0], raw=raw)
                    if len(args) == 2:
                        return self.eval(
                            "(⊃∆)(%s)2⊃∆" % aplfn, args[0], args[1], raw=raw
                        )
                    raise APLError("Function must be monadic or dyadic.")

                __fn.aplfn = aplfn
                self.ops += 1
                return __fn

            return __op

        def interrupt(self):
            """Send a strong interrupt to the Dyalog interpreter."""
            if self.pid:
                Interrupt.interrupt(self.pid)

        def tradfn(self, tradfn):
            """Define a tradfn or tradop on the APL side.

            Input must be string, the lines of which will be passed to ⎕FX."""

            Message(Message.EXEC, tradfn).send(self.conn.outfile)
            reply = self.conn.expect(Message.OK)

            if reply.type == Message.ERR:
                raise APLError(jsobj=str(reply.data, "utf-8"))
            else:
                return self.fn(str(reply.data, "utf-8"))

        def repr(self, aplcode):
            """Run an APL expression, return string representation"""

            # send APL message
            Message(Message.REPR, aplcode).send(self.conn.outfile)
            reply = self.conn.expect(Message.REPRRET)

            if reply.type == Message.ERR:
                raise APLError(jsobj=str(reply.data, "utf-8"))
            else:
                return reply.data

        def fix(self, code):
            """2⎕FIX an APL script. It will become available in the workspace.
            Input may be a string or a list."""

            # implemented using eval
            if not type(code) is str:
                code = str(code, "utf-8")

            if not type(code) is list:
                code = code.split("\n")  # luckily APL has no multiline strings

            return self.eval("2⎕FIX ∆", *code)

        def eval(self, aplexpr, *args, **kwargs):
            """Evaluate an APL expression. Any extra arguments will be exposed
            as an array ∆. If `raw' is set, the result is not converted to a
            Python representation."""

            if not type(aplexpr) is str:
                # this should be an UTF-8 string
                aplexpr = str(aplexpr, "utf8")

            # normalize (remove superfluous whitespace and newlines, add in ⋄s where
            # necessary)

            aplexpr = (
                "⋄".join(x.strip() for x in aplexpr.split("\n") if x.strip())
                .replace("{⋄", "{")
                .replace("⋄}", "}")
                .replace("(⋄", "(")
                .replace("⋄)", ")")
            )

            payload = APLArray.from_python([aplexpr, args], apl=self).toJSONString()
            Message(Message.EVAL, payload).send(self.conn.outfile)

            reply = self.conn.expect(Message.EVALRET)

            if reply.type == Message.ERR:
                raise APLError(jsobj=reply.data)

            answer = APLArray.fromJSONString(reply.data)

            if "raw" in kwargs and kwargs["raw"]:
                return answer
            else:
                return answer.to_python(self)

    @staticmethod
    def APLClient(DEBUG=False, dyalog=None, forceTCP=False):
        """Start an APL client. This function returns an APL instance."""

        # if on Windows, use TCP always
        if os.name == "nt" or "CYGWIN" in platform.system():
            forceTCP = True

        if forceTCP:
            # use TCP
            inpipe = outpipe = IPC.TCPIO()  # TCP connection is bidirectional
            outarg = "TCP"
            inarg = str(inpipe.startServer())
        else:
            # make two named pipes
            inpipe = IPC.FIFO()
            outpipe = IPC.FIFO()
            inarg = inpipe.name
            outarg = outpipe.name

        if DEBUG:
            print("in: ", inarg)
            print("out: ", outarg)

        # start up Dyalog
        if not DEBUG:
            RunDyalog.dystart(outarg, inarg, dyalog=dyalog)

        if forceTCP:
            # wait for Python to make the connection
            inpipe.acceptConnection()
        else:
            # start the writer first
            outpipe.openWrite()
            inpipe.openRead()

        if DEBUG:
            print("Waiting for PID...")
        connobj = Connection(inpipe, outpipe, signon=False)

        # ask for the PID
        pidmsg = connobj.expect(Message.PID)

        if pidmsg.type == Message.ERR:
            raise APLError(pidmsg.data)
        else:
            pid = int(pidmsg.data)
            if DEBUG:
                print("Ok! pid=%d" % pid)
            apl = connobj.apl
            apl.pid = pid
            apl.DEBUG = DEBUG

            # if we are on Windows, hide the window
            if os.name == "nt":
                WinDyalog.hide(pid)

            return apl

    def __init__(self, infile, outfile, signon=True):
        self.infile = infile
        self.outfile = outfile
        self.apl = Connection.APL(self)
        self.isSlave = False
        if signon:
            Message(Message.PID, str(os.getpid())).send(self.outfile)
            self.isSlave = True

    def runUntilStop(self):
        """Receive messages and respond to them until STOP is received."""
        self.stop = False

        while not self.stop:

            sig = ignoreInterrupts()

            # is there a message available?
            msg = Message.recv(self.infile, block=False)

            setInterrupts(sig)

            if not msg is None:
                # yes, respond to it
                self.respond(msg)

    def expect(self, msgtype):
        """Expect a certain type of message. If such a message or an error
        is received, return it; if a different message is received, then
        handle it and go back to waiting for the right type of message."""

        while True:
            s = None
            try:
                # only turn off interrupts if the APL side is in control
                if self.isSlave:
                    s = ignoreInterrupts()
                msg = Message.recv(self.infile)

                if msg.type in (msgtype, Message.ERR):
                    return msg
                else:
                    if self.isSlave:
                        allowInterrupts()
                    self.respond(msg)
            except KeyboardInterrupt:
                self.apl.interrupt()
            finally:
                if self.isSlave:
                    setInterrupts(s)
                pass

    def respond(self, message):
        # Add ctrl+c signal handling
        try:
            self.respond_inner(message)
        except KeyboardInterrupt:
            # If there is an interrupt during 'respond', then that means
            # the Python side was interrupted, and we need to tell the
            # APL this.
            Message(Message.ERR, "Interrupt").send(self.outfile)

    def respond_inner(self, message):
        """Respond to a message"""

        t = message.type
        if t == Message.OK:
            # return 'OK' to such messages
            Message(Message.OK, message.data).send(self.outfile)

        elif t == Message.PID:
            # this is interpreted as asking for the PID
            Message(Message.PID, str(os.getpid())).send(self.outfile)

        elif t == Message.STOP:
            # send a 'STOP' back in acknowledgement and set the stop flag
            self.stop = True
            Message(Message.STOP, "STOP").send(self.outfile)

        elif t == Message.REPR:
            # evaluate the input and send the Python representation back
            try:
                val = repr(eval(message.data))
                Message(Message.REPRRET, val).send(self.outfile)
            except Exception as e:
                Message(Message.ERR, repr(e)).send(self.outfile)

        elif t == Message.EXEC:
            # execute some Python code in the global context
            sig = None
            try:
                sig = allowInterrupts()

                script = message.data
                if type(script) is bytes:
                    script = str(script, "utf-8")

                PyEvaluator.executeInContext(script, self.apl)
                Message(Message.OK, "").send(self.outfile)
            except Exception as e:
                Message(Message.ERR, repr(e)).send(self.outfile)
            finally:
                setInterrupts(sig)

        elif t == Message.EVAL:
            # evaluate a Python expression with optional arguments
            # expected input: APLArray, first elem = expr string, 2nd elem = arguments
            # output, if not an APLArray already, will be automagically converted

            sig = None
            try:
                sig = allowInterrupts()
                val = APLArray.fromJSONString(message.data)
                # unpack code
                if val.rho != [2]:
                    raise MalformedMessage(
                        "EVAL expects a ⍴=2 array, but got: %s" % repr(val.rho)
                    )

                if not isinstance(val[[0]], APLArray):
                    raise MalformedMessage("First argument must contain code string.")

                code = val[[0]].to_python(self.apl)
                if not type(code) in (str, bytes):
                    raise MalformedMessage(
                        "Code element must be a string, but got: %s" % repr(code)
                    )

                # unpack arguments
                args = val[[1]]
                if not isinstance(val[[1]], APLArray) or len(val[[1]].rho) != 1:
                    raise MalformedMessage("Argument list must be rank-1 array.")

                result = PyEvaluator(code, args, self).go().toJSONString()
                Message(Message.EVALRET, result).send(self.outfile)
            except Exception as e:
                # raise
                Message(Message.ERR, repr(e)).send(self.outfile)
            finally:
                setInterrupts(sig)

        elif t == Message.DBGSerializationRoundTrip:
            # this is a debug message. Deserialize the contents, print them to stdout, reserialize and send back
            try:
                print("Received data: ", message.data)
                print("---------------")

                aplarr = APLArray.fromJSONString(message.data)
                serialized = aplarr.toJSONString()

                print("Sending back: ", serialized)
                print("---------------")

                Message(Message.DBGSerializationRoundTrip, serialized).send(
                    self.outfile
                )
            except Exception as e:
                Message(Message.ERR, repr(e)).send(self.outfile)
        else:
            Message(
                Message.ERR,
                "unknown message type #%d / data:%s" % (message.type, message.data),
            ).send(self.outfile)
