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

            
def windows_find_dyalog():
    # find the Dyalog path in the registry
    import _winreg
    try:
        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r'Software\Dyalog')
        r=''; i=0
        while True:
            r=_winreg.EnumKey(key,i)
            if "Dyalog" in r: break 
            i+=1
        key = _winreg.OpenKey(key, r)
        dir, _ = _winreg.QueryValueEx(key, "dyalog")
        return dir + r'\dyalog.exe'
    except WindowsError:
        raise RuntimeError("Dyalog not found.")
    
def dystart(port, dyalog=None):
    if os.name=='posix':
        if not dyalog: dyalog="dyalog" # assume it's just on the path
        
        thread.start_new_thread(dythread, (port,), {"dyalog":dyalog})
    elif os.name=='nt':
        
        # look up dyalog in registry
        if not dyalog: dyalog=windows_find_dyalog()
        
        # This is a horrible hack
        # Write the necessary port to a dyalog script
        with file("WinPort.dyalog", "w") as f:
            f.write("""
                :Namespace WinPort
                port←%d
                :EndNamespace
            """%port)
       
        # use a .dyapp to include it and run it
        #Popen([dyalog, 'WinPySlave.dyapp'], stdin=None, stdout=None, stderr=None, close_fds=True)
        os.system("start WinPySlave.dyapp")
        
    else:
        raise RuntimeError("OS not supported: " + os.name)


