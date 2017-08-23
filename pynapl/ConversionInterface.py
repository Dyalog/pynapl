# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import json

# Any object that can do from_python will inherit from this class
class Sendable(object):
    def toJSONDict(self):
        raise NotImplemented()

    def toJSONString(self):
        return json.dumps(self, cls=ArrayEncoder, ensure_ascii=False)

# Any object that can do to_python will inherit from this class
class Receivable(object):
    def to_python(self, apl=None):
        raise NotImplemented()

# Generalized JSON encoder
class ArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Sendable):
            return obj.toJSONDict()
        elif isinstance(obj, complex): # special-cased
            return {"real": obj.real, "imag": obj.imag}
        else:
            return json.JSONEncoder.default(self, obj)

