# -*- coding: utf-8 -*-

"""Dyalog APL <> Python bridge"""

import Array
import APLPyConnect

def APL(debug=False):
    """Start an APL interpreter"""
    return APLPyConnect.Connection.APLClient(DEBUG=debug)

APLArray = Array.APLArray
