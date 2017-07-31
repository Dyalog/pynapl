# Run a Dyalog instance in the background and start the Python client
# -*- coding: utf-8 -*-

from __future__ import absolute_import 
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import sys, os, threading, platform
from subprocess import Popen, PIPE

# Use python 3 types in python 2
if sys.version_info.major == 2:
    bytes, str = str, unicode

SCRIPTFILE=os.path.realpath(__file__)

script="""
    ⎕PW←32767
    {}2⎕FIX'file://%s'
    port←%d
    Py.StartAPLSlave port
    )OFF
"""

def to_bytes(x):
    if type(x) is str: return x.encode('utf-8')
    else: return x

def posix_dythread(port, dyalog="dyalog"):
    # find the path, Py.dyalog should be in the same folder
    path=to_bytes(os.path.dirname(SCRIPTFILE))+b'/Py.dyalog'
    
    # Run the Dyalog instance in this thread
    p=Popen([dyalog, b'-script'], stdin=PIPE, preexec_fn=os.setpgrp)
    p.communicate(input=script.encode('utf8')%(path,port))

def cyg_convert_path(path, type):
    return Popen([b"cygpath",type,path],stdout=PIPE).communicate()[0].split(b"\n")[0]
    
def win_dythread(dyalog, cygwin=False):

    startupinfo = None
    preexec_fn = None
    
    if not cygwin:
        # not cygwin 
        # hide the window
        # imported here because STARTUPINFO only exists on Windows
        import subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwflags = subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    elif cygwin:
        # cygwin: we need to setpgrp like on Linux or Dyalog will crash
        preexec_fn = os.setpgrp 
    
        
    path=to_bytes(os.path.dirname(SCRIPTFILE))+b'/WinPySlave.dyapp'
    if cygwin: path=cyg_convert_path(path, b"--windows") 
    Popen([dyalog, b'DYAPP='+path], 
          startupinfo=startupinfo,
          preexec_fn=preexec_fn).communicate()
    
def cygwin_find_dyalog():
    # the horrible bastard child of two operating systems
    
    try:
        # find which versions of Dyalog are installed
        regpath = b"\\user\\Software\\Dyalog"
        dyalogs = Popen([b"regtool",b"list",regpath],stdout=PIPE).communicate()[0].split(b"\n")
        
        # we only want unicode versions for obvious reasons
        dyalogs = [d for d in dyalogs if b'unicode' in d.lower()]
        if not dyalogs: raise RuntimeError("Cannot find a suitable Dyalog APL.")
        
        # we want the highest version
        # the format should be: Dyalog APL-[WS](-64)? version Unicode
        dyalogs.sort(key=lambda x: float(x.split()[2]))
        dyalog = dyalogs[0]
        
        # find the path to that dyalog
        path = Popen([b"regtool",b"get",regpath+b"\\"+dyalog+b"\\dyalog"],stdout=PIPE)\
                  .communicate()[0].split(b"\n")[0]
        path += b"\\dyalog.exe"          
        
        # of course, now it needs to be converted back into Unix format...
        path = cyg_convert_path(path, b"--unix")
        return path
    except:
        #raise
        raise RuntimeError("Cannot find a suitable Dyalog APL.")
            
def windows_find_dyalog():
    # find the Dyalog path in the registry
    import _winreg 
    
    try:
        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, br'Software\Dyalog')
        r=b''; i=0
        while True:
            r=_winreg.EnumKey(key,i)
            if b"Dyalog" in r and b"unicode" in r.lower(): break 
            i+=1
        key = _winreg.OpenKey(key, r)
        dir, _ = _winreg.QueryValueEx(key, b"dyalog")
        return dir + br'\dyalog.exe'
    except WindowsError:
        raise RuntimeError("Dyalog not found.")
    
def dystart(port, dyalog=None):
    if os.name=='posix' and not 'CYGWIN' in platform.system():
        if not dyalog: dyalog=b"dyalog" # assume it's just on the path
        
        #thread.start_new_thread(posix_dythread, (port,), {"dyalog":dyalog})
        t=threading.Thread(target=lambda:posix_dythread(port,dyalog=dyalog))
        t.daemon=True
        t.start()

    elif os.name=='nt' or 'CYGWIN' in platform.system():
        
        # look up dyalog in registry
        if not dyalog: 
            if 'CYGWIN' in platform.system():
                dyalog=cygwin_find_dyalog()
            else:
                dyalog=windows_find_dyalog()
        
        # This is a horrible hack
        # Write the necessary port to a dyalog script
        with open(to_bytes(os.path.dirname(SCRIPTFILE))+b'/WinPort.dyalog', "wb") as f:
            f.write(to_bytes("""
                :Namespace WinPort
                port←%d
                :EndNamespace
            """)%port)
       
        #thread.start_new_thread(win_dythread, (), {"dyalog":dyalog, 
        #                    'cygwin':'CYGWIN' in platform.system()})
        t=threading.Thread(
                       target=lambda:win_dythread(dyalog=dyalog,
                       cygwin='CYGWIN' in platform.system()))

        t.daemon=True
        t.start()
        #Popen([dyalog, 'WinPySlave.dyapp'], stdin=None, stdout=None, stderr=None, close_fds=True)
        
    else:
        raise RuntimeError("OS not supported: " + os.name)


