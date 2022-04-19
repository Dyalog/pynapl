# Code to communicate with the Windows version of Dyalog

import os
import threading
from ctypes import byref, c_uint, cdll, create_unicode_buffer, windll
from subprocess import PIPE, Popen

pidMainWindows = {}


# convert to bytes
def to_bytes(x):
    if type(x) is str:
        return x.encode("utf-8")
    else:
        return x


def from_bytes(x):
    if type(x) is bytes:
        return str(x, "utf-8")
    else:
        return x


# find the library
try:
    user32 = windll.user32
except NameError:
    # this might be Cygwin
    try:
        user32dll_winpath = to_bytes(os.environ["WINDIR"]) + rb"\System32\User32.dll"
        user32dll_cygpath = (
            Popen([b"cygpath", b"--unix", user32dll_winpath], stdout=PIPE)
            .communicate()[0]
            .split(b"\n")[0]
        )

        # On Python 2, the input should be a string of bytes; on Python 3
        # it wants Unicode. 'Popen' works only with bytes in any case.
        user32dll_cygpath = from_bytes(user32dll_cygpath)
        user32 = cdll.LoadLibrary(user32dll_cygpath)
    except (KeyError, OSError):
        # not Windows at all
        class X(object):
            def __getattr__(self, attr):
                raise RuntimeError(
                    "Cannot call Windows functions from Unix (%s)." % attr
                )

        user32 = X()


def interrupt(pid):
    """Tell the Dyalog window to interrupt"""

    interruptWindow(findWindow(pid))


def hide(pid):
    hwnd = findWindow(pid)
    # user32.ShowWindow(hwnd, False)


def findWindow(pid):
    """Find the Dyalog window associated with the given process"""

    if pid in pidMainWindows:
        return pidMainWindows[pid]

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
            user32.GetWindowTextW(curwnd, title, length + 1)

            # check whether it is the main window by checking if
            # "Dyalog APL" is in the title...
            if "Dyalog APL" in title.value:
                # this is the one
                pidMainWindows[pid] = curwnd
                return curwnd

        # try the next window
        curwnd = user32.GetWindow(curwnd, 2)  # 2 = GW_HWNDNEXT

    return None  # couldn't find it


def interruptWindow(hwnd):
    """Tell Dyalog APL to interrupt the running code.

    hwnd must be the handle to the main Dyalog window."""
    threading.Thread(target=lambda: user32.PostMessageA(hwnd, 273, 133, 0)).start()

    # 273 = WM_COMMAND
    # 133 = the Actions -> Interrupt menu
