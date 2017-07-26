# Run a Dyalog instance in the background and start the Python client
# -*- coding: utf-8 -*-

import os, thread, platform
from subprocess import Popen, PIPE

SCRIPTFILE=os.path.realpath(__file__)

script="""
    ⎕PW←32767
    {}2⎕FIX'file://%s'
    port←%d
    Py.StartAPLSlave port
    )OFF
"""

def posix_dythread(port, dyalog="dyalog"):
    # find the path, Py.dyalog should be in the same folder
    path=os.path.dirname(SCRIPTFILE)+'/Py.dyalog'
    # Run the Dyalog instance in this thread
    p=Popen([dyalog, '-script'], stdin=PIPE)
    p.communicate(input=script%(path,port))

def cyg_convert_path(path, type):
    return Popen(["cygpath",type,path],stdout=PIPE).communicate()[0].split("\n")[0]
    
def win_dythread(dyalog, cygwin=False):
    path=os.path.dirname(SCRIPTFILE)+'/WinPySlave.dyapp'
    if cygwin: path=cyg_convert_path(path, "--windows") 
    Popen([dyalog, 'DYAPP='+path]).communicate()
    
def cygwin_find_dyalog():
    # the horrible bastard child of two operating systems
    
    try:
        # find which versions of Dyalog are installed
        regpath = "\\user\\Software\\Dyalog"
        dyalogs = Popen(["regtool","list",regpath],stdout=PIPE).communicate()[0].split("\n")
        
        # we only want unicode versions for obvious reasons
        dyalogs = [d for d in dyalogs if 'unicode' in d.lower()]
        if not dyalogs: raise RuntimeError("Cannot find a suitable Dyalog APL.")
        
        # we want the highest version
        # the format should be: Dyalog APL-[WS](-64)? version Unicode
        dyalogs.sort(key=lambda x: float(x.split()[2]))
        dyalog = dyalogs[0]
        
        # find the path to that dyalog
        path = Popen(["regtool","get",regpath+"\\"+dyalog+"\\dyalog"],stdout=PIPE)\
                  .communicate()[0].split("\n")[0]
        path += "\\dyalog.exe"          
        
        # of course, now it needs to be converted back into Unix format...
        path = cyg_convert_path(path, "--unix")
        return path
    except:
        #raise
        raise RuntimeError("Cannot find a suitable Dyalog APL.")
            
def windows_find_dyalog():
    # find the Dyalog path in the registry
    import _winreg 
    
    try:
        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r'Software\Dyalog')
        r=''; i=0
        while True:
            r=_winreg.EnumKey(key,i)
            if "Dyalog" in r and "unicode" in r.lower(): break 
            i+=1
        key = _winreg.OpenKey(key, r)
        dir, _ = _winreg.QueryValueEx(key, "dyalog")
        return dir + r'\dyalog.exe'
    except WindowsError:
        raise RuntimeError("Dyalog not found.")
    
def dystart(port, dyalog=None):
    if os.name=='posix' and not 'CYGWIN' in platform.system():
        if not dyalog: dyalog="dyalog" # assume it's just on the path
        
        thread.start_new_thread(posix_dythread, (port,), {"dyalog":dyalog})
    elif os.name=='nt' or 'CYGWIN' in platform.system():
        
        # look up dyalog in registry
        if not dyalog: 
            if 'CYGWIN' in platform.system():
                dyalog=cygwin_find_dyalog()
            else:
                dyalog=windows_find_dyalog()
        
        # This is a horrible hack
        # Write the necessary port to a dyalog script
        with file(os.path.dirname(SCRIPTFILE)+'/WinPort.dyalog', "w") as f:
            f.write("""
                :Namespace WinPort
                port←%d
                :EndNamespace
            """%port)
       
        thread.start_new_thread(win_dythread, (), {"dyalog":dyalog, 
                            'cygwin':'CYGWIN' in platform.system()})
        
        #Popen([dyalog, 'WinPySlave.dyapp'], stdin=None, stdout=None, stderr=None, close_fds=True)
        
    else:
        raise RuntimeError("OS not supported: " + os.name)


