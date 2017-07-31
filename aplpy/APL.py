# -*- coding: utf-8 -*-

"""Dyalog APL <> Python bridge"""

from __future__ import absolute_import
from __future__ import division

from . import Array
from . import APLPyConnect

def APL(debug=False, dyalog=None):
    """Start an APL interpreter
    
    If "dyalog" is set, this is taken to be the path to the Dyalog interpreter.
    If it is not, a suitable Dyalog APL interpreter will be searched for on the
    path (on Unix/Linux) or in the registry (on Windows).
    """
    return APLPyConnect.Connection.APLClient(DEBUG=debug, dyalog=dyalog)

APLArray = Array.APLArray
APLError = APLPyConnect.APLError
