# -*- coding: utf-8 -*-

"""Dyalog APL <> Python interface"""

import threading

import APLPyConnect
import Array
import IPC


def APL(debug=False, dyalog=None, forceTCP=False):
    """Start an APL interpreter
    
    If "dyalog" is set, this is taken to be the path to the Dyalog interpreter.
    If it is not, a suitable Dyalog APL interpreter will be searched for on the
    path (on Unix/Linux) or in the registry (on Windows).
    
    """
    return APLPyConnect.Connection.APLClient(DEBUG=debug, dyalog=dyalog, forceTCP=forceTCP)

APLArray = Array.APLArray
APLError = APLPyConnect.APLError

def client(inp, outp, threaded=True):
    """Allow an APL interpreter to connect to the running Python instance.
    
    This is probably only useful for interactive sessions, as the APL instance
    will need to be started first, and its port number given to this function.

    As the APL side will be in control, you will not be able to access APL
    from Python.
    
    Interrupt handling will _not work_. 
    """

    def run():
        if inp.lower() == 'tcp':
            # then 'outp' should be a port number
            sock = IPC.TCPIO()
            sock.connect('localhost', int(outp))
            conn=APLPyConnect.Connection(sock,sock)
        else:
            # open two pipoes
            i_f = IPC.FIFO(inp)
            i_f.openRead()

            o_f = IPC.FIFO(outp)
            o_f.openWrite()

            conn=APLPyConnect.Connection(i_f, o_f)
       
        conn.runUntilStop()


    if threaded:
        # start it on a separate thread
        threading.Thread(target=run).start()
    else:
        run()

# convenience method
def tcpclient(port, threaded=True):
    """Allow an APL interpreter to connect to the running Python instance."""
    client('TCP', port, threaded)



