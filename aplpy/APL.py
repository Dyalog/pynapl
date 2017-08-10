# -*- coding: utf-8 -*-

"""Dyalog APL <> Python bridge"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

from . import Array
from . import APLPyConnect

import socket, threading, sys, types

if sys.version_info.major >= 3:
    import queue
else:
    import Queue as queue

def APL(debug=False, dyalog=None, forceTCP=False):
    """Start an APL interpreter
    
    If "dyalog" is set, this is taken to be the path to the Dyalog interpreter.
    If it is not, a suitable Dyalog APL interpreter will be searched for on the
    path (on Unix/Linux) or in the registry (on Windows).
    
    """
    return APLPyConnect.Connection.APLClient(DEBUG=debug, dyalog=dyalog, forceTCP=forceTCP)

APLArray = Array.APLArray
APLError = APLPyConnect.APLError

def client(port, threaded=True):
    """Allow an APL interpreter to connect to the running Python instance.
    
    This is probably only useful for interactive sessions, as the APL instance
    will need to be started first, and its port number given to this function.
    
    The connection can run in a separate thread, so that the Python session
    remains interactive as well. The APL side can be told to run an asynchronous
    message handler, such that the `apl.*' functions will work as normal.
    
    Interrupt handling will _not work_. 
    """

    try:
        sock=socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
        sock.connect(('localhost',port))
    except:
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.connect(('localhost',port))

    def thread(asyncHandlerQ=None):
        conn = APLPyConnect.Connection(sock)
        if not asyncHandlerQ is None:
            apl = asyncHandlerQ.get()
        else:
            apl = None
        conn.runUntilStop(asyncHandler=apl)
        sock.close()

    if threaded:
        q = queue.Queue(1)
        x = AsyncAPL()
        q.put(x)
        t=threading.Thread(target=lambda: thread(q))
        t.daemon = True
        t.start()
        return x
    else:
        thread()
        return None


class AsyncAPL(object):
    """Allows running APL code on a separate thread.
    
    The thread you run this on will wait until an answer is available,
    if one is expected.
    """

    __apl = None
    __queue_in = None
    __queue_out = None

    def __init__(self):
        self.__queue_in = queue.Queue()
        self.__queue_out = queue.Queue()

    def _setAPL(self, apl):
        self.__apl = apl

    def _process(self):
        if self.__apl is None:
            raise RuntimeError("APL not set.")

        try:
            fn = self.__queue_in.get(block=False)
            out = fn()

            # if the result is a function, which it could be, then we need to wrap it
            # so that it also uses the queue for communication
            if type(out) in (types.FunctionType, types.BuiltinFunctionType):
                def __thread_fn(*args, **kwargs):
                    self.__queue_in.put(lambda: out(*args, **kwargs))
                    return self.__queue_out.get()
                self.__queue_out.put(__thread_fn)
            else:
                self.__queue_out.put(out)

        except queue.Empty:
            pass # nothing to do

    def __getattr__(self, name):
        if self.__apl is None:
            raise RuntimeError("APL not set.")

        if hasattr(self.__apl,name):
            attr = getattr(self.__apl,name)
            def __fn(*args, **kwargs):
                self.__queue_in.put(lambda: attr(*args, **kwargs))
                return self.__queue_out.get()
            return __fn
        else:
            raise AttributeError("No such attribute: %s" % name)
