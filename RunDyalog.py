# Run a Dyalog instance in the background and start the Python client
# -*- coding: utf-8 -*-

import os, thread
from subprocess import Popen, PIPE

script="""
    ⎕PW←32767
    {}2⎕FIX'file://Py.dyalog'
    port←%d
    Py.StartAPLSlave port
    )OFF
"""

def dythread(port, dyalog="dyalog"):
    # Run the Dyalog instance in this thread
    p=Popen([dyalog, '-script'], stdin=PIPE)
    p.communicate(input=script%port)

def dystart(port, dyalog="dyalog"):
    if os.name=='posix':
        thread.start_new_thread(dythread, (port,), {"dyalog":dyalog})
    elif os.name=='nt':
        raise NotImplementedError("TODO: implement Python APL initiation on Windows")
    else:
        raise RuntimeError("OS not supported: " + os.name)


