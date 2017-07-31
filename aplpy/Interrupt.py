# Platform-specific code to send interrupts to an APL instance 

from __future__ import absolute_import
from __future__ import division

from . import WinDyalog
import os, platform, signal  

def interrupt(pid):
    if os.name=='nt' or 'CYGWIN' in platform.system():
        # standard Windows, use the Windows API
        WinDyalog.interrupt(pid)
    elif os.name=='posix' and not 'CYGWIN' in platform.system():
		# standard Unix, send SIGINT 
		os.kill(pid, signal.SIGINT)
    else:
        raise RuntimeError("OS not supported")
		
