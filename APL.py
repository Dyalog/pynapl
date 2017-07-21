# -*- coding: utf-8 -*-

"""Dyalog APL <> Python bridge"""

import Array
import APLPyConnect

def APL():
    """Start an APL interpreter"""
    return APLPyConnect.Connection.APLClient()

APLArray = Array.APLArray
