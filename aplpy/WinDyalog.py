# Code to communicate with the Windows version of Dyalog

from __future__ import absolute_import
from __future__ import division

from ctypes import *
from subprocess import Popen, PIPE
import threading, os


pidMainWindows = {}

# find the library
try:
    user32 = windll.user32
except NameError:
    # this might be Cygwin
    try:
        user32dll_winpath = os.environ['WINDIR'] + r'\System32\User32.dll'
        user32dll_cygpath = Popen(['cygpath','--unix',user32dll_winpath],
                             stdout=PIPE).communicate()[0].split("\n")[0]
        user32 = cdll.LoadLibrary(user32dll_cygpath)
    except (KeyError, OSError):
        # not Windows at all
        class X(object):
            def __getattr__(self,attr):
                raise RuntimeError("Cannot call Windows functions from Unix (%s)." % attr)
    
        user32 = X()
    
def interrupt(pid):
    """Tell the Dyalog window to interrupt"""

    interruptWindow(findWindow(pid))

def hide(pid):
    hwnd = findWindow(pid)
    user32.ShowWindow(hwnd, False)
    
def findWindow(pid):
    """Find the Dyalog window associated with the given process"""
    
    if pid in pidMainWindows: return pidMainWindows[pid]
    
    cur_pid = c_uint()
    
    # Get a handle to the desktop and scan all its children
    curwnd = user32.GetTopWindow(0)
    
    while curwnd:
        # to whom does this window belong? 
        user32.GetWindowThreadProcessId(curwnd, byref(cur_pid))
        
        if cur_pid.value == pid:
            # this one belongs to us
            
            length = user32.GetWindowTextLengthW(curwnd)
            title = create_unicode_buffer(length + 1)
            user32.GetWindowTextW(curwnd,title,length+1)
			
            # check whether it is the main window by checking if
            # "Dyalog APL" is in the title...
            if "Dyalog APL" in title.value:
                # this is the one
                pidMainWindows[pid] = curwnd
                return curwnd
		
        # try the next window
        curwnd = user32.GetWindow(curwnd, 2) # 2 = GW_HWNDNEXT
    
    return None # couldn't find it
	
def interruptWindow(hwnd):
    """Tell Dyalog APL to interrupt the running code.
    
    hwnd must be the handle to the main Dyalog window."""
    threading.Thread(target=lambda:user32.PostMessageA(hwnd, 273, 133, 0)).start()

    # 273 = WM_COMMAND
    # 133 = the Actions -> Interrupt menu
	
	
	
