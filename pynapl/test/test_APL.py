# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from .. import APL

import unittest
import sys
import random

class TestAPL(unittest.TestCase):
    def setUp(self):
        self.apl = APL.APL()
    def tearDown(self):
        self.apl.stop()

    def test_eval(self):
        """Run some APL code"""
        self.assertEqual(4, self.apl.eval("2+2"))

    def test_function(self):
        """Import an APL function and use it"""
        sum = self.apl.fn("+/")
        # monadic
        self.assertEqual(4, sum([2, 2]))
        # dyadic
        self.assertEqual([10,15,20,25,30,35],
                sum(5, range(10)))

        # niladic is invalid for this function, so should raise APLError
        self.assertRaises(APL.APLError, sum)
    
    def test_operator(self):
        """Import an APL operator"""
        
        fpow = self.apl.op("⍣")

        # test on an APL function
        apl_add = self.apl.fn("+")
        apl_add_x5 = fpow(apl_add, 5)
        self.assertEqual(15, apl_add_x5(1, 10))

        # test on Python function
        py_add_called=[0]
        def py_add(x,y):
            py_add_called[0] += 1
            return x+y
        py_add_x5 = fpow(py_add, 5)
        self.assertEqual(15, py_add_x5(1, 10))

        # this should have called py_add 5 times
        self.assertEqual(5, py_add_called[0])

    def test_tradfn(self):
        """Define a tradfn, import it, and call it"""
        
        tradfn = self.apl.tradfn("""
        z←tradfn x
        z←x+x
        """)

        self.assertEqual(4, tradfn(2))

    def test_bidirectional(self):
        """Have APL call back into the Python code"""
        CALLBACK_IN, CALLBACK_OUT = 20, 40

        callback_data = [CALLBACK_OUT]
        def callback(x):
            y = callback_data[0]
            callback_data[0] = x
            return y

        self.apl.callback = callback
        test = self.apl.tradfn("""
        z←test x;callback
        callback←(py.PyFn'APL.callback').Call
        z←callback x
        """)

        self.assertEqual(CALLBACK_OUT, test(CALLBACK_IN))
        self.assertEqual(CALLBACK_IN, callback_data[0])

    def test_fix(self):
        """⎕FIX"""

        names = self.apl.fix("""
        :Namespace Test
            foo←42
        :EndNamespace
        """)

        self.assertEqual(["Test"], names)
        self.assertEqual(42, self.apl.eval("Test.foo"))

    def test_apl_objects(self):
        """Transfer APL objects to Python"""
        
        self.apl.fix("""
        :Class Foo
            :Field Public n←42
            ∇init x
                :Access Public
                :Implements Constructor
                n←x
            ∇
        :EndClass
        """)

        foo = self.apl.eval("+foo←⎕NEW Foo 42")  # store object on both sides
        
        self.assertEqual(foo.n, 42)              # the object must contain 42
        foo.n = 88                               # we must be able to change it
        self.assertEqual(foo.n, 88)              # the change must stick
        self.assertEqual(88, self.apl.eval("foo.n"))  # and must be reflected in APL
        
        # we must be able to pass the ref back to APL, where it must resolve to exactly the
        # same object
        self.assertTrue(self.apl.fn("{foo≡⍵}")(foo))
        
        bar = self.apl.eval("⎕NEW Foo 99")       # make a new object and don't store it in APL
        self.assertEqual(bar.n, 99)              # it must transfer through
        self.assertEqual(foo.n, 88)              # it must not have changed the other one
        bar.n = 77                               # we must be able to change it
        self.assertEqual(bar.n, 77)              # the change must stick
        self.assertEqual(foo.n, 88)              # and not affect the other one

        # we must be able to pass the ref back to APL and use it
        self.assertEqual(77, self.apl.fn('{⍵.n}')(bar))

        self.apl.fn('{⍵.n←66}')(bar)             # and we must be able to change it there
        self.assertEqual(66, bar.n)              # and the change must be reflected in Python


        


