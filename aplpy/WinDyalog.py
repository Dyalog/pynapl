# Code to communicate with the Windows version of Dyalog

from ctypes import *
import thread

pidMainWindows = {}

def interrupt(pid):
    """Tell the Dyalog window to interrupt"""

    interruptWindow(findWindow(pid))

def hide(pid):
    hwnd = findWindow(pid)
    windll.user32.ShowWindow(hwnd, False)
    
def findWindow(pid):
    """Find the Dyalog window associated with the given process"""
    
    if pid in pidMainWindows: return pidMainWindows[pid]
    
    user32 = windll.user32
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
    thread.start_new_thread(windll.user32.PostMessageA,(hwnd, 273, 133, 0))
    # 273 = WM_COMMAND
    # 133 = the Actions -> Interrupt menu
	
	
	