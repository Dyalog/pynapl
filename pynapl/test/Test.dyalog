:Namespace Test

    :Section Startup / shutdown
        py ← ⍬
        ∇StartUp v
            ⍝ Initialize a Python
            ⎕EX'py'
            py ← ⎕NEW #.Py.Py ('Version' v)
        ∇

        ∇ShutDown
            py.Stop
            ⎕EX'py'
        ∇
    :EndSection

    :Section Tests
        ⍝⍝⍝ test the connection ⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝

        ⍝ Evaluate a simple expression and see if it works
        ∇ r←TEST_01⍙2_plus_2
            ⍙EV←4
            r←py.Eval '2+2'
        ∇

        ⍝ Evaluate a list and see if it works
        ∇ r←TEST_02⍙py_list
            ⍙EV←1 2 3 4
            r←py.Eval '[1,2,3,4]'
        ∇

        ⍝⍝⍝ test the serializer ⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝⍝
        ∇ r←TEST_03⍙serialize_complex_obj
            ⍝ this is hopefully a complex enough object to catch most weirdness
            ⍙EV←('ABCD'(5 5⍴⎕A)(⍳4 4)(⍬⍬⍬)(1 2 3⍴⊂'Quack'))
            r←'⍞'py.Eval⊂⍙EV
        ∇

        ⍝ cause an error on the Python side and see if we can catch it
        ∇ r←TEST_04⍙error_handling
            ⍙EV←1 1
            r←0 0
            :Trap 11 ⍝ domain error
                {}py.Eval '5/0'
            :Else
                r[1]←1 ⍝ it worked
            :EndTrap

            ⍝ the Python instance must survive this
            r[2] ← py.Eval '1'
        ∇

        ⍝ call into Python from APL and see if it works
        ⍙test_callback_val←⍬

        ∇ r←TEST_05⍙python_callback;pycall;X;Y
            X Y←10 20
            ⍙EV←Y X

            ⍙test_callback_val←Y
            pycall←(py.PyFn 'APL.fn("#.Test.CALLBACK")').Call

            X←pycall X
            Y←⍙test_callback_val

            r←X Y
        ∇

        ∇ r←CALLBACK x
            r←⍙test_callback_val
            ⍙test_callback_val←x
        ∇

        ⍝ test Python statement execute
        ∇ r←TEST_06⍙python_exec
            ⍙EV←10 20 30
            py.Exec'x=10'
            py.Exec'y=20'
            py.Exec'z=30'
            r←py.Eval'[x,y,z]'
        ∇

        ⍝ test Python script_follows
        ∇ r←TEST_07⍙ScriptFollows;fn
            ⍙EV←4

            py.Exec #.Py.ScriptFollows
            ⍝ def fn(x):
            ⍝    return x*2

            fn←(py.PyFn'fn').Call
            r←fn 2
        ∇

        ⍝ test importing module
        ∇ r←TEST_08⍙modules;json
            ⍙EV←1 2 3 4 5

            ⍝ import a module
            json←py.Import'json'
            ⍝ call methods from it
            str←json.dumps ⊂⍙EV
            r←json.loads ⊂str 
        ∇

        ⍝ test that we can pass an object back and forth
        ∇ r←TEST_09⍙objects;x
            ⍙EV←⍬
            r←⍬

            ⍝ define an object
            py.Exec #.Py.ScriptFollows
            ⍝ class X(object):
            ⍝   def __init__(self, n):
            ⍝      self.n = n


            ⍝ instantiate it and bring it into APL
            x←py.Eval'X(42)'

            ⍝ try to access it from APL (should give 42)
            ⍙EV,←42 ⋄ r,←x.n

            ⍝ try to access it from Python (should also give 42)
            ⍙EV,←42 ⋄ r,←'⎕.n' py.Eval ⊂x

            ⍝ try to set it from APL
            x.n←88

            ⍝ try to access it from APL (should now give 88)
            ⍙EV,←88 ⋄ r,←x.n

            ⍝ try to access it from Python (should now also give 88)
            ⍙EV,←88 ⋄ r,←'⎕.n' py.Eval ⊂x

            ⍝ store a reference on the Python side and change that
            'x' py.Set x
            py.Exec 'x.n=99'

            ⍝ this change should be reflected in APL
            ⍙EV,←99 ⋄ r,←x.n

        ∇

    :EndSection

    :Section Utility functions
        StartsWith←{⍺≡(≢⍺)↑⍵}
        StripFrom←{1↓(∨\⍺=⍵)/⍵}
        Filter←{(⍺⍺ ⍵)/⍵}
    :EndSection

    :Section Test framework
        ⍙EV←⍬

        ⍝ A test is any function in here that starts with 'TEST_'
        ∇tests←FindTests
            tests←('TEST_'∘StartsWith¨) Filter ⎕NL-3
        ∇

        ⍝ A test must set ⍙EV to the expected value.
        ⍝ ¯1 = unexpected crash, 0 = fail, 1 = ok
        RunTest←{
            0::¯1⊣msg∘←⍕⎕DMX.(EN EM Message)
            ⍙EV≡⍎⍵⊣msg∘←''
        }

        ⍝ Run one test
        ∇v←RunOneTest test
            StartUp
            v←⍎test
            ShutDown
        ∇

        ⍝ Run all tests
        ∇summary←RunTests v;tests;rslts
            StartUp v
            rslts←{
                (⍳⍴⍵)(⍵{
                    ⍞←'Running ',(¯3↑⍕⍺),'/',(¯3↑⍕⍴⍺⍺),': ',30↑'⍙'StripFrom⍵
                    rs←RunTest ⍵
                    ⍞←' ',⊃'CRASH' 'FAIL' 'OK'[2+rs]
                    ⍞←' ',msg
                    ⍞←⎕TC[2]
                    rs
                })¨⍵
            }FindTests

            summary←'Crash' 'Fail' 'OK',⍪⊃(⊂¯1 0 1)+.=rslts
            ShutDown
        ∇
    :EndSection
:EndNamespace
