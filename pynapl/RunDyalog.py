# Run a Dyalog instance in the background and start the Python client

import os
import platform
import re
import threading
from subprocess import PIPE, Popen

SCRIPTFILE = os.path.realpath(__file__)

script = """
    ⎕PW←32767
    {}2⎕FIX'file://%s'
    {}2⎕FIX'file://%s'
    infile←'%s'
    outfile←'%s'
    Py.StartAPLSlave infile outfile
    )OFF
"""


def to_bytes(x):
    if not type(x) is bytes:
        return x.encode("utf-8")
    else:
        return x


def pystr(x):
    """Given a string of bytes, returns either an ASCII string
    or an Unicode string, depending on what the running version
    of Python would expect."""
    if type(x) is bytes:
        return str(x, "utf-8")
    return x


def posix_dythread(inf, outf, dyalog=b"dyalog"):
    # find the path to IPC.dyalog
    ipcpath = to_bytes(os.path.dirname(SCRIPTFILE)) + b"/IPC.dyalog"

    # find the path, Py.dyalog should be in the same folder
    path = to_bytes(os.path.dirname(SCRIPTFILE)) + b"/Py.dyalog"

    # Run the Dyalog instance in this thread
    p = Popen([dyalog, b"-script"], stdin=PIPE, preexec_fn=os.setpgrp)
    s = script % (pystr(ipcpath), pystr(path), inf, outf)
    p.communicate(input=s.encode("utf8"))


def cyg_convert_path(path, type):
    return Popen([b"cygpath", type, path], stdout=PIPE).communicate()[0].split(b"\n")[0]


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

    path = to_bytes(os.path.dirname(SCRIPTFILE)) + b"/WinPySlave.dyapp"
    if cygwin:
        path = cyg_convert_path(path, b"--windows")

    dyalog = pystr(dyalog)
    arg = pystr(b"DYAPP=" + path)

    x = Popen([dyalog, arg], startupinfo=startupinfo, preexec_fn=preexec_fn)
    x.communicate()


def mac_find_dyalog():
    # it wouldn't be the Mac if it weren't special

    apls = sorted(
        [
            (x.group(0), x.group(1))
            for x in [
                re.match(r"^Dyalog-(\d+(\.\d+)?)\.app$", x)
                for x in os.listdir("/Applications")
            ]
            if x
        ],
        key=lambda x: -float(x[1]),
    )

    if not apls:
        raise RuntimeError("Dyalog not found.")

    # take the Dyalog APL with the highest version number
    apl = apls[0][0]
    apl = "/Applications/" + apl + "/Contents/Resources/Dyalog/dyalog"
    return apl


def cygwin_find_dyalog():
    # the horrible bastard child of two operating systems

    try:
        # find which versions of Dyalog are installed
        regpath = b"\\user\\Software\\Dyalog"
        dyalogs = (
            Popen([b"regtool", b"list", regpath], stdout=PIPE)
            .communicate()[0]
            .split(b"\n")
        )

        # we only want unicode versions for obvious reasons
        dyalogs = [d for d in dyalogs if b"unicode" in d.lower()]
        if not dyalogs:
            raise RuntimeError("Cannot find a suitable Dyalog APL.")

        # we want the highest version
        # the format should be: Dyalog APL-[WS](-64)? version Unicode
        dyalogs.sort(key=lambda x: float(x.split()[2]))
        dyalog = dyalogs[0]

        # find the path to that dyalog
        path = (
            Popen(
                [b"regtool", b"get", regpath + b"\\" + dyalog + b"\\dyalog"],
                stdout=PIPE,
            )
            .communicate()[0]
            .split(b"\n")[0]
        )
        path += b"\\dyalog.exe"

        # of course, now it needs to be converted back into Unix format...
        path = cyg_convert_path(path, b"--unix")
        return path
    except:
        # raise
        raise RuntimeError("Cannot find a suitable Dyalog APL.")


def windows_find_dyalog():
    # find the Dyalog path in the registry
    try:
        import winreg
    except:
        import _winreg as winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, pystr(rb"Software\Dyalog"))
        r = pystr(b"")
        i = 0
        while True:
            r = winreg.EnumKey(key, i)
            if pystr(b"Dyalog") in r and pystr(b"unicode") in r.lower():
                break
            i += 1
        key = winreg.OpenKey(key, r)
        dir, _ = winreg.QueryValueEx(key, pystr(b"dyalog"))
        return to_bytes(dir) + rb"\dyalog.exe"
    except WindowsError:
        raise RuntimeError("Dyalog not found.")


def dystart(inf, outf, dyalog=None):
    if os.name == "posix" and not "CYGWIN" in platform.system():
        if not dyalog:
            if "Darwin" in platform.system():
                # this is a Mac, try to find Dyalog in /Applications
                dyalog = to_bytes(mac_find_dyalog())
            else:
                dyalog = b"dyalog"  # assume it's just on the path, in a normal Unix installation

        t = threading.Thread(target=lambda: posix_dythread(inf, outf, dyalog=dyalog))
        t.daemon = True
        t.start()

    elif os.name == "nt" or "CYGWIN" in platform.system():
        if inf != "TCP":
            raise NotImplementedError(
                "Only TCP connections are supported under Windows."
            )

        # look up dyalog in registry
        if not dyalog:
            if "CYGWIN" in platform.system():
                dyalog = cygwin_find_dyalog()
            else:
                dyalog = windows_find_dyalog()

        # This is a horrible hack
        # Write the necessary port to a dyalog script
        with open(
            to_bytes(os.path.dirname(SCRIPTFILE)) + b"/WinPort.dyalog", "wb"
        ) as f:
            f.write(
                to_bytes(
                    """
                :Namespace WinPort
                port←'%d'
                :EndNamespace
            """
                    % int(outf)
                )
            )

        t = threading.Thread(
            target=lambda: win_dythread(
                dyalog=dyalog, cygwin="CYGWIN" in platform.system()
            )
        )

        t.daemon = True
        t.start()

    else:
        raise RuntimeError("OS not supported: " + os.name)
