﻿⍝∇:require =/IPC.dyalog
:Namespace Py
    ⎕IO ⎕ML←1

    :Section Helper functions to include Python code in APL code

        ⍝ thanks to Adám for these functions 
        ∇ r←ScriptFollows
            r←2↓∊(⎕UCS 13 10)∘,¨Follows
        ∇

        ∇ r←Follows;n;x
            n←⎕XSI{1++/∧\⍵∘≡¨(⊃⍴⍵)↑¨⍺}(⍕⎕THIS),'.'
            r←↓(∨\~∧⌿' '=x)/[2]x←1↓[2]↑(↓∧⍀∨\'⍝'=↑x)/¨x←(1+n⊃⎕LC)↓↓(180⌶)n⊃⎕XSI
        ∇ 

    :EndSection


    ⍝ Make a namespace out of ('name' value) pairs
    ∇r←MkNS pairs;name;value
        r←⎕NS''
        :For (name value) :In pairs
            name r.{⍎⍺,'←⍵'} value
        :EndFor
    ∇

    ⍝ Retrieve the path from the namespace
    ∇r←ScriptPath
        ⍝r←SALT_Data.SourceFile

        ⍝ Adám's SourceFile function
        r←{ ⍝ Get pathname to sourcefile for item ⍵
            c←⎕NC⊂,⍕⍵
            c=2.1:(SALT_Var_Data.VD[;1]⍳⊂⍵(⊢,~)'#.')⊃SALT_Var_Data.VD[;2],⊂''
            c∊3.1 3.2 4.1 4.2:1↓⊃('§'∘=⊂⊢)∊¯2↑⎕NR ⍵
            (r←326=⎕DR ⍵)∨c∊9+0.1×⍳8:{6::'' ⋄ ''≡f←⊃(4∘⊃¨(/⍨)(⍵≡⊃)¨)5177⌶⍬:⍵.SALT_Data.SourceFile ⋄ f}⍎⍣(~r)⊢⍵
            ''
        }⎕THIS
    ∇

    ⍝ Start an APL slave and connect to the given input and output pipes
    ∇StartAPLSlave (inf outf);py

        py←⎕NEW Py (⊂('Client' (inf outf)))
    ∇

    ⍝ Make an error object
    ∇err←DMXErr dmx
        err←⎕NS''
        err.Message←dmx.EM
        err.DMX←dmx
        err←⎕JSON err
    ∇

    ∇err←MSGErr msg
        err←⎕NS''
        err.Message←msg
        err←⎕JSON err
    ∇

    :Class JSONSerializer
        :Field Public Instance pyclass

        ⍝ deserialize
        ∇ r←pyclass deserialize json
            :Access Public Shared
            r←pyclass decode ⎕JSON json
        ∇

        ∇ r←pyclass decode obj
            :Access Public Shared

            :If 9.1≠⎕NC⊂'obj'
                ⍝ automatically decoded by ⎕JSON
                r←obj
                :Return
            :EndIf

            :If 0≠⎕NC'obj.ns'
                ⍝ an encoded namespace
                r←pyclass decodeNS obj.ns
                :Return
            :EndIf

            :If 0≠⎕NC'obj.id'
                ⍝ a Python object wrapper
                r←pyclass decodeOW obj
                :Return
            :EndIf

            :If 0≠⎕NC'obj.rid'
                ⍝ a reference to one of our own objects
                r←pyclass.⍙Access obj.rid
                :Return
            :EndIf

            :If 0≠⎕NC'obj.imag'
                ⍝ an encoded complex number
                r←obj.real+0j1×obj.imag
                :Return
            :EndIf

            ⍝ if not a simple object or a namespace,
            ⍝ it must then be an array

            :If (0=≢obj.data)∧0≠⎕NC'obj.t'
                ⍝ empty array with type hint
                :If 0=obj.t
                    r←obj.r⍴⍬
                :ElseIf 1=obj.t
                    r←obj.r⍴''
                :Else
                    ⎕SIGNAL⊂('EN' 11)('Message' 'Invalid type hint')
                :EndIf
            :Else
                ⍝ otherwise, reconstruct the array as given
                r←obj.shape⍴(pyclass∘decode)¨⊃¨obj.data
            :EndIf
        ∇

        ∇ r←pyclass decodeOW ns
            r←⍙PythonObject.⍙MkInst (pyclass ns)
        ∇   

        ∇ r←pyclass decodeNS ns;child;children;dec
            r←⎕NS''

            children←ns.⎕NL-2 9

            :For child :In children
                dec←pyclass decode ns.⍎child
                child r.{⍎⍺,'←⍵'}dec
            :EndFor
        ∇

        ∇init pyc
            :Access Public
            :Implements Constructor
            pyclass←pyc
        ∇

        ⍝ serialize
        ∇ r←pyclass serialize obj;enc;ns;encr
            :Access Public Shared
            encr←⎕NEW #.Py.JSONSerializer pyclass
            enc←encr.encode obj
            :If 0=⎕NC'enc.r'
                ns←⎕NS''
                ns.r←⍬
                ns.d←,enc
                addTypeHint ns
                enc←ns
            :EndIf
            r←⎕JSON enc
        ∇

        ⍝ add a type hint to an encoded array
        ∇ addTypeHint obj
            :Trap 16
                ⍝ if the prototype is a namespace, this raises
                ⍝ NONCE ERROR, thus this hacky trap
                obj.t←' '=⊃0⍴∊obj.d
            :Else
                ⍝ we don't really do prototypes, so let's
                ⍝ just say the type is numeric
                obj.t←0
            :EndTrap
        ∇

        ⍝ create something JSONizable from an APL object
        ∇ r←{taboo}encode obj;arrns
            :Access Public 

            :If 0=⎕NC'taboo' ⋄ taboo←⍬ ⋄ :EndIf

            ⍝ if this is an object that supports its own encoding, use that
            :If 0≠⎕NC⊂'obj.⍙encode'
                r←obj.⍙encode
                :Return
            :EndIf

            :If ~(⎕NC⊂'obj')∊2.1 2.2 9.1
                ⍝ try to encode it using the pyclass
                r←taboo encode (pyclass.Obj obj)
                :Return
            :EndIf

            :If 0=≡obj
                ⍝ The object is simple, return it

                :If 9=⊃⎕NC'obj'
                    ⍝ the object is a namespace, encapsulate it
                    r←taboo encapsulate obj
                :ElseIf ⍬≡0↑obj
                :AndIf 0≠11○obj
                    ⍝ it is a complex number, which JSON does not support
                    ⍝ encode it
                    r←⎕NS''
                    r.(real imag)←9 11○obj
                :Else
                    ⍝ it is a normal number or character
                    r←obj
                :EndIf
            :Else

                ⍝ the object is some kind of array,
                ⍝ we need to encode each element
                r←⎕NS''
                r.r←⍴obj
                r.d←,(⊂taboo)encode¨obj
                addTypeHint r
            :EndIf

        ∇

        ⍝ encapsulate namespace
        ∇ r←{taboo}encapsulate obj;ns;children;child;enc
            :Access Public

            :If 0=⎕NC'taboo' ⋄ taboo←⍬ ⋄ :EndIf

            ⍝ Prevent nested loop
            :If obj∊taboo ⋄ r←⍬ ⋄ :Return ⋄ :EndIf

            :If 9≠⎕NC'obj'
                ⍝ not a namespace, return it unchanged
                r←obj
                :Return
            :EndIf

            ns←⎕NS''

            ⍝ find child variables and namespaces
            children←obj.⎕NL-2 9

            ⍝ loop through the children, encoding each and
            ⍝ storing it under the same name in the namespace
            :For child :In children
                enc←(taboo,obj)encode obj.⍎child
                child ns.{⍎⍺,'←⍵'}enc
            :EndFor

            ⍝ encapsulate it in a namespace with a single field
            ⍝ 'ns', so we can tell it apart from the other
            ⍝ namespaces
            r←⎕NS''
            r.ns←ns
        ∇

    :EndClass

    :Class UnixInterface
        ⍝ Functions to interface with Unix OSes

        ∇ r←GetPID
            :Access Public Shared
            ⍝ get current process ID
            :If 0=⎕NC'#.NonWindows.GetPID'
                'NonWindows'#.⎕CY'quadna.dws'
                #.NonWindows.Setup
            :EndIf
            r←#.NonWindows.GetPID
        ∇

        ∇ r←GetPath fname
            :Access Public Shared
            r←(⌽∨\⌽'/'=fname)/fname
        ∇

        ∇ {py} StartPython (argfmt program inf outf majorVersion);cmd;pypath;arg
            :Access Public Shared
            :If 0=≢argfmt
                ⍝ Use default argument format: <program> <in> <out>
                argfmt←'''⍎'' ''→'' ''←'''
            :EndIf

            :If 2=⎕NC'py'
            :andif 0≠≢py
                ⍝use given path
                pypath←py
            :else
                ⍝find python on path
                :Trap 11
                    pypath←⊃⎕SH'which python',∊(majorVersion>2)↑⊂⍕majorVersion
                :Else
                    ⎕SIGNAL⊂('EN'999)('Message' 'Cannot find Python on the path.')
                :EndTrap
            :endif
            arg←('⍎'⎕R{program})('→'⎕R{inf})('←'⎕R{outf})argfmt
            ⎕SH pypath,' ',arg,' >/dev/null &'

        ∇

        ∇ Kill pid
            :Access Public Shared
            ⎕SH 'kill ', (⍕pid), ' 2>/dev/null'
        ∇


        ∇ Interrupt pid
            :Access Public Shared
            ⎕SH 'kill -2 ',⍕pid
        ∇

    :EndClass     


    :Class WindowsInterface
        ⍝ Functions to interface with Windows using .NET
        ⍝ NOTE: will keep track of the process itself rather than use the pid as in Linux

        :Using System.Diagnostics,System.dll
        :Using Microsoft.Win32,mscorlib.dll

        :Field Private Instance pyProcess←⍬

        ∇ r←GetPID
            :Access Public Instance     
            r←Process.GetCurrentProcess.Id
        ∇

        ∇ r←GetPath fname
            :Access Public Shared
            r←(⌽∨\⌽'\'=fname)/fname
        ∇

        ∇ {py} StartPython (argfmt program inf outf majorVersion);pypath;arg;nonstandard
            :Access Public Instance                                                    
            nonstandard←0
            :If 0=≢argfmt
                ⍝ Use default argument format: <program> <port>
                argfmt←'"⍎" → ←'
            :Else
                nonstandard←1
            :EndIf

            :If 2=⎕NC'py' 
            :andIf 0≠≢py
                ⍝ use given path
                pypath←py     
                nonstandard←1
            :ElseIf 0=≢pypath←FindPythonInRegistry majorVersion
                ⍝ can't find it in registry either
                ⎕SIGNAL⊂('EN'999)('Message' 'Cannot find Python in registry.')
            :EndIf

            arg←('⍎'⎕R{program})('→'⎕R{inf})('←'⎕R{outf})argfmt
            :Trap 90  

                pyProcess←⎕NEW Process
                pyProcess.StartInfo.FileName←pypath
                pyProcess.StartInfo.Arguments←arg  
                :If ~nonstandard
                    ⍝ this will crash e.g. Blender, so only do it to known Python
                    pyProcess.StartInfo.RedirectStandardOutput←1
                    pyProcess.StartInfo.RedirectStandardError←1 
                    pyProcess.StartInfo.UseShellExecute←0
                    pyProcess.StartInfo.CreateNoWindow←1
                :EndIf  
                {}pyProcess.Start ⍬
            :Else
                ⎕SIGNAL⊂('EN'999)('Message' 'Cannot start Python')
            :EndTrap
        ∇

        ∇ path←FindPythonInRegistry majorVersion;rk;rka;rkb;comp;ver
            :Access Public Shared   

            ⍝ attempt to find Python in the registry
            ⍝ (see: https://www.python.org/dev/peps/pep-0514/)

            ⍝ first position: HKEY_CURRENT_USER/Software/Python  
            rka←Registry.CurrentUser   
            rka←rka.OpenSubKey('Software' 0)  ⋄ →('[Null]'≡⍕rka)/localmachine 
            rkb←rka.OpenSubKey('Python' 0)    ⋄ →('[Null]'≡⍕rkb)/localmachine 
            rk←rkb ⋄ →foundPython

            localmachine:
            ⍝ second postion: HKEY_LOCAL_MACHINE/Software/Python      
            rka←Registry.LocalMachine                     
            rka←rka.OpenSubKey('Software' 0)  ⋄ →('[Null]'≡⍕rka)/fail 
            rkb←rka.OpenSubKey('Python'   0)  ⋄ →('[Null]'≡⍕rkb)/wow6234 
            rk←rkb ⋄ →foundPython

            wow6234:
            ⍝ third position: HKEY_LOCAL_MACHINE/Software/WOW6234Node/Python 
            rkb←rka.OpenSubKey('WOW6432Node' 0) ⋄ →('[Null]'≡⍕rkb)/fail
            rka←rkb.OpenSubKey('Python' 0)    ⋄ →('[Null]'≡⍕rka)/fail
            rk←rka ⋄ →foundPython

            foundPython:
            ⍝ this will get the first Python it finds, even if your Python
            ⍝ is not from the official distribution (PythonCore)
            ⍝ it will prefer PythonCore if it's in there
            ⍝ PyLauncher is reserved and does not contain a Python, so it is dropped
            comp←rk.GetSubKeyNames~⊂'PyLauncher'
            comp←⊃comp[⍒comp≡¨⊂'PythonCore']
            rk←rk.OpenSubKey(comp 0)          ⋄ →('[Null]'≡⍕rk)/fail

            ⍝ find highest installed version matching major version
            ver←{
                vers←{⊃⊃(//)⎕VFI(∧\⍵∊⎕D,'.')/⍵}¨⍵
                valid←majorVersion=⌊vers
                (⊃⍒valid×vers)⊃⍵                
            }rk.GetSubKeyNames  

            rk←rk.OpenSubKey(ver 0)           ⋄ →('[Null]'≡⍕rk)/fail    
            rk←rk.OpenSubKey('InstallPath' 0) ⋄ →('[Null]'≡⍕rk)/fail
            path←rk.GetValue⊂''
            path,←'\python.exe'

            :Return

            fail:
            path←''
            :Return

        ∇

        ∇ Kill ignored
            ⍝ the rest of the program will pass a PID in for both OSes,
            ⍝ in Windows we don't need it, so we ignore it.
            :Access Public Instance  
            :Trap 6 90
                ⍝ The process is supposed to exit on its own, so there's a good chance
                ⍝ this will give an exception, thus the trap.
                pyProcess.Kill ⍬                             
            :EndTrap
        ∇           

        ∇ Interrupt pid
            ⍝ Just to be inconsistent, this function _does_ use the PID that is
            ⍝ passed in. There's somewhat of a reason for it: it makes debugging
            ⍝ a little easier.
            :Access Public Instance

            ⍝ Windows kernel black magic
            '⍙AC'⎕NA'U4 kernel32|AttachConsole U4'
            '⍙FC'⎕NA'U4 kernel32|FreeConsole'
            '⍙GCCE'⎕NA'U4 kernel32|GenerateConsoleCtrlEvent U4 U4'
            '⍙SCCH'⎕NA'P kernel32|SetConsoleCtrlHandler P U4' 

            :If ⍙AC pid ⍝ attach a console to Python
                {}⍙SCCH 0 1 ⍝ turn off our own ctrl handler
                {}⍙GCCE 0 0 ⍝ ctrl+c to Python
                ⎕DL÷4 ⍝ it takes Windows a while to process it
                {}⍙FC ⍬ ⍝ free the console
            :Else
                ⎕←'Failed to attach to process. Interrupt not sent.'
            :EndIf 
        ∇

    :EndClass


    ⍝ This class can represent a Python object
    ⍝ 'Py' will make instances of these, using which you can represent
    ⍝ the Python object.

    ⍝ (All the names start with ⍙ since that doesn't occur in Python)
    :Class ⍙PythonObject
        :Field Private ⍙id
        :Field Private ⍙va
        :Field Private ⍙fn
        :Field Private ⍙py

        ∇⍙dont_do_this
            :Access Public
            :Implements Constructor
            ⎕SIGNAL⊂('EN'11)('Cannot instantiate Python class from APL.')
        ∇

        ∇⍙init(pyclass ns)
            :Access Public
            :Implements Constructor
            ⍙id←ns.id
            ⍙va←ns.va
            ⍙fn←ns.fn
            ⍙py←pyclass
        ∇

        ∇r←⍙Ref
            :Access public
            r←⍙id
        ∇

        ∇r←⍙encode
            :Access Public
            ⍝ return the reference ID to Python
            r←⎕NS''
            r.rid←⍙id
        ∇

        ⍝⍝ Make a python instance
        ∇z←⍙MkInst (pyclass ns);cls;clstxt;va;fn;clns;fn_mangle
            :Access Public Shared

            clstxt← ⊂':Class ',ns.cls,' : #.Py.⍙PythonObject'

            ⍝ add a constructor
            clstxt,←⊂ '∇ ⍙init(pyclass ns)'
            clstxt,←⊂ '  :Access Public'
            clstxt,←⊂ '  :Implements Constructor :Base (pyclass ns)'
            clstxt,←(~pyclass.noDF)/⊂ '  :Trap 0 1000 ⋄ ⎕DF ''repr(⎕)'' pyclass.Eval ⎕THIS ⋄ :Else ⋄ ⎕SIGNAL ⍙MkErr⎕DMX ⋄ :EndTrap'
            clstxt,←⊂ '∇'

            ⍝ add a field by which we can retrieve the class name
            clstxt,←⊂ ':Field Public ⍙CLASSNAME←''',ns.cls,''''
            
            ⍝ add in properties for all the variables
            :For va :In ns.va
                :If '.'∊va ⋄ :Continue ⋄ :EndIf
                
                ⍝ add in a cache field
                clstxt,←⊂ ':Field Private ⍙CACHE⍙',va,'←⍬'
                
                clstxt,←⊂ ':Property ',va
                clstxt,←⊂ ':Access Public'
                clstxt,←⊂ '∇ r←get'
                ⍝clstxt,←⊂ '  :If ⍙CACHE⍙',va,'≢⍬ ⋄ r←⍙CACHE⍙',va,' ⋄ →0 ⋄ :EndIf' ⍝ use cache if it's there
                clstxt,←⊂ '  :Trap 0 1000 ⋄ r←⍙Get ''',va,''' ⋄ :Else ⋄ ⎕SIGNAL ⍙MkErr⎕DMX ⋄ :EndTrap'
                ⍝clstxt,←⊂ '  →(0=⎕NC⊂''r.⍙CLASSNAME'')/0' ⍝ if not a Python object, no cache
                ⍝clstxt,←⊂ '  →(r.⍙CLASSNAME≢''module'')/0' ⍝ if not a Python module, no cache
                ⍝clstxt,←⊂ '  ⍙CACHE⍙',va,'←r'
                clstxt,←⊂ '∇'
                clstxt,←⊂ '∇ set v'
                clstxt,←⊂ '  :Trap 0 1000 ⋄ ''',va,''' ⍙Set v.NewValue ⋄ :Else ⋄ ⎕SIGNAL ⍙MkErr⎕DMX ⋄ :EndTrap'
                ⍝clstxt,←⊂ '  ⍙CACHE⍙',va,'←⍬'
                clstxt,←⊂ '∇'
                clstxt,←⊂ ':EndProperty'

                clstxt,←⊂ ':Property ∆',va
                clstxt,←⊂ ':Access Public'
                clstxt,←⊂ '∇ r←get'
                clstxt,←⊂ '  :Trap 0 1000 ⋄ r←⍙Get∆ ''',va,''' ⋄ :Else ⋄ ⎕SIGNAL ⍙MkErr⎕DMX ⋄ :EndTrap'
                clstxt,←⊂ '∇'
                clstxt,←⊂ ':EndProperty'
            :EndFor

            ⍝ add in functions for all the functions
            :For fn :In ns.fn
                :If '.'∊fn ⋄ :Continue ⋄ :EndIf

                clstxt,←⊂ '∇{z}←{kwargs} ∆',fn,' args'
                clstxt,←⊂ '  :Access Public'
                clstxt,←⊂ '  :If 0=⎕NC''kwargs'' ⋄ kwargs←⍬ ⋄ :EndIf'
                clstxt,←⊂ '  args←,args'
                clstxt,←⊂ '  :Trap 0 1000 ⋄ z←''',fn,''' ⍙Call∆ args kwargs ⋄ :Else ⋄ ⎕SIGNAL ⍙MkErr⎕DMX ⋄ :EndTrap'
                clstxt,←⊂ '∇'

                ⍝ Unfortunately, Dyalog APL implements property getters and setters
                ⍝ by defining functions called 'get_property' and 'set_property'. 
                ⍝ This means that if a variable 'foo' exists, and a function 'get_foo'
                ⍝ also exists, this will cause a conflict on the APL side.
                ⍝
                ⍝ If this is the case, we mangle the function names by prepending '⍙'.

                :If (⊂4↑fn)∊'get_' 'set_'
                :AndIf (⊂4↓fn)∊ns.va
                    fn_mangle←'⍙',fn
                :Else
                    fn_mangle←fn
                :EndIf

                clstxt,←⊂ '∇{z}←{kwargs} ',fn_mangle,' args'
                clstxt,←⊂ '  :Access Public'
                clstxt,←⊂ '  :If 0=⎕NC''kwargs'' ⋄ kwargs←⍬ ⋄ :EndIf'
                clstxt,←⊂ '  args←,args'
                clstxt,←⊂ '  :Trap 0 1000 ⋄ z←''',fn,''' ⍙Call args kwargs ⋄ :Else ⋄ ⎕SIGNAL ⍙MkErr⎕DMX ⋄ :EndTrap'
                clstxt,←⊂ '∇'
            :EndFor

            clstxt,←⊂':EndClass'

            clns←⎕NS'' 
            ⍝ fix the class
            cls←clns.⎕FIX clstxt


            ⍝ instantiate it
            z←⎕NEW cls (pyclass ns)
        ∇

        ∇⍙destroy
            :Access Private
            :Implements Destructor
            ⍝ at least _try_ to tell Python to decrease the refcount,
            ⍝ but don't crash the whole thing if it doesn't work for some reason
            :Trap 0
                {}'APL._release(⎕)' ⍙py.Eval ⊂⍙id
            :EndTrap
        ∇

        ⍝ Access Values
        ∇z←⍙Get var
            :Access Public
            z←'getattr(APL._access(⎕),⎕)' ⍙py.Eval ⍙id var
        ∇

        ⍝ Access Values
        ∇z←⍙Get∆ var
            :Access Public
            z←'APL.obj(getattr(APL._access(⎕),⎕))' ⍙py.Eval ⍙id var
        ∇


        ∇var ⍙Set val
            :Access Public
            {} 'setattr(APL._access(⎕),⎕,⎕)' ⍙py.Eval ⍙id var val
        ∇

        ∇var ⍙SetRaw val
            :Access Public
            {} 'setattr(APL._access(⎕),⎕,⍞)' ⍙py.Eval ⍙id var val
        ∇    

        ⍝ Call Functions
        ∇{z}←fname ⍙Call (args kwargs)
            :Access Public

            :If 9≠⎕NC'kwargs'
                kwargs←#.Py.MkNS kwargs
            :EndIf

            z←'getattr(APL._access(⎕),⎕)(*⎕,**⎕)' ⍙py.Eval ⍙id fname args kwargs
        ∇

        ⍝ Make an error message
        ∇err←⍙MkErr dmx
            :Access Public
            err←⊂('EN'(dmx.EN))('Message'(dmx.Message))
        ∇

        ⍝ Call Functions
        ∇{z}←fname ⍙Call∆ (args kwargs)
            :Access Public

            :If 9≠⎕NC'kwargs'
                kwargs←#.Py.MkNS kwargs
            :EndIf

            z←'APL.obj(getattr(APL._access(⎕),⎕)(*⎕,**⎕))' ⍙py.Eval ⍙id fname args kwargs
        ∇
        
        ⍝ Update DF to be the object's __repr__
        ∇{z}←⍙DF
            :Access Public
            :Trap 0 1000
                z←'repr(APL._access(⎕))' ⍙py.Eval ⊂⍙id
                ⎕DF z
            :EndTrap
        ∇

    :EndClass

    ⍝ This class stores references to instances of other objects, to keep track of them
    ⍝ so the Python side can use references to them. 
    :Class ObjectStore
        :Field Private objects

        ⍝ columns
        :Field Private REF←1
        :Field Private OBJ←2
        :Field Private CNT←3

        :Field Private refno←0

        ∇init
            :Access Public
            :Implements Constructor
            objects←0 3⍴⍬ ⍝ matrix: 
        ∇

        ⍝ get next reference number
        ∇ref←NextRef
            refno+←1
            ref←(' '≠ref)/ref←40 0⍕refno
        ∇

        ⍝ Retrieve object reference
        ∇obj←Retrieve ref;loc
            :Access Public
            loc←objects[;REF]⍳⊂ref
            ⎕SIGNAL(loc>≢objects)/⊂('EN'6)('Message' 'Invalid object reference')
            obj←⊃objects[loc;OBJ]
        ∇ 

        ⍝ Store an object (called from the Python side)
        ∇ref←Store obj;loc
            :Access Public
            ⍝ do we already have it?
            :If (loc←objects[;OBJ]⍳obj)≤≢objects
                ⍝ yes, increase the refcount and return the reference we already had
                objects[loc;CNT]+←1
                ref←⊃objects[loc;REF]
            :Else
                ⍝ we don't, add it with refcount 1
                ref←NextRef
                objects⍪←⍉⍪ref obj 1
            :EndIf
        ∇

        ⍝ Release an object (called from the Python side)
        ∇Release ref;loc
            :Access Public
            loc←objects[;REF]⍳⊂ref
            ⎕SIGNAL(loc>≢objects)/⊂('EN'6)('Message' 'Invalid object reference')
            objects[loc;CNT]-←1
            objects⌿⍨←objects[;CNT]>0
        ∇        
    :EndClass

    ⍝ This can wrap an APL object and then be sent to Python
    :Class ObjectWrapper
        :Field Private store
        :Field Private ref

        ∇init (store_ obj)
            :Access Public
            :Implements Constructor

            store←store_
            ref←store.Store obj
        ∇

        ∇enc←⍙encode;obj
            :Access Public
            obj←store.Retrieve ref
            enc←⎕NS''

            enc.id←ref
            enc.va←obj.⎕NL-2 9
            enc.fn←obj.⎕NL-3
            ⍝ operators aren't necessary because classes can't have public operators anyway
        ∇
    :EndClass




    ⍝ Connect to 
    :Class Py

        when←/⍨

        :Field Public noDF←0      ⍝ boolean that decides whether ⎕DF should be set to repr(⎕) on Python classes. 
        
        ⍝ errors
        :Field Private PYERR←11   ⍝ error raised when Python returns an error
        :Field Private BROKEN←990 ⍝ error raised when the object is not in an usable state
        :Field Private BUGERR←15  ⍝ error raised when the cause is an internal bug

        :Field Private ready←0
        :Field Private pid←¯1
        :Field Private os

        :Field Private lastError←''

        :Field Private filename←'APLBridgeSlave.py'

        :Field Private pypath←''

        ⍝ this holds the namespace in which APL code sent from the Python side
        ⍝ will be evaluated.
        :Field Private pyaplns←⍬

        ⍝ Wait to connect to an external APLBridgeSlave.py rather than launch
        ⍝ one.
        :Field Private attachToExistingPython←0

        ⍝ Print debug messages
        :Field Private debugMsg←0

        ⍝ Major version of Python to use. Default: 3
        ⍝ This only really matters for which interpreter to launch,
        ⍝ the APL side of the code does not (currently) care about the
        ⍝ difference.
        :Field Private majorVersion←3

        ⍝ In/Out FIFO
        :Field Private fifoIn
        :Field Private fifoOut

        ⍝ This is set to 1 if this is our Python (so we need to signal it)
        :Field Private signalPython←0

        ⍝ This field can be set to 0 to disallow interrupts completely
        :Field Private noInterrupts←0

        ⍝ Holds references to object instances sent to Python, so they can be accessed
        ⍝ and aren't garbage-collected.
        :Field Private objectStore←⍬

        :Section Python object references
            ⍝ Wrap an object so that a reference to it can be sent to Python
            ∇ r←Obj obj
                :Access Public
                r←⎕NEW ObjectWrapper (objectStore obj)
            ∇

            ⍝ Called by the Python side to access an APL object
            ∇ r←⍙Access ref
                :Access Public
                r←objectStore.Retrieve ,ref
            ∇

            ⍝ Called by the Python side to release an APL object
            ∇ ⍙Release ref
                :Access Public
                objectStore.Release ,ref
            ∇
        :EndSection

        ⍝ JSON serialization/deserialization
        :Section JSON serialization/deserialization
            ⍝ Serialize a (possibly nested) array
            serialize←{⎕THIS #.Py.JSONSerializer.serialize ⍵}

            ⍝ Deserialize a (possibly nested) array
            ⍝ Pass along an instance of the class so we can pass _that_ along to Python object wrappers
            deserialize←{⎕THIS #.Py.JSONSerializer.deserialize ⍵}

            :Section JSON serialization debug code
                ⍝ Send an array through the serialization code on both sides
                ⍝ and see what comes back. No other mangling is done, the Python
                ⍝ side just gets an APLArray.
                ∇out←TestArrayRoundTrip in;sin;sout;msg
                    :Access Public
                    sin ← serialize in

                    msg sout←{⍵ ExpectAfterSending (⍵ sin)}Msgs.DBGSerializationRoundTrip

                    :If msg≠Msgs.DBGSerializationRoundTrip
                        ⎕←'Received other msg: ' msg sout
                        →0
                    :EndIf

                    out ← deserialize sout
                ∇
            :EndSection
        :EndSection

        :Section Network functions

            ⍝Message type "constants"
            :Namespace Msgs
                OK←0
                PID←1
                STOP←2
                REPR←3
                EXEC←4
                REPRRET←5

                EVAL←10
                EVALRET←11

                DBGSerializationRoundTrip ← 253
                DBG←254
                ERR←255
            :EndNamespace

            ⍝ Run a client on a given a port
            ∇ RunClient (in out);rv;ok;msg;data

                :If in≡'TCP'
                    ⍝ use TCP ('out' will be the port number)
                    #.IPC.TCP.Init
                    fifoIn ← ⎕NEW #.IPC.TCP.Connection
                    fifoOut ← fifoIn
                    fifoIn.Connect 'localhost' (⍎out)
                :Else 
                    ⍝ bind the sockets
                    fifoIn ← ⎕NEW #.IPC.OS.FIFO in
                    fifoOut ← ⎕NEW #.IPC.OS.FIFO out

                    ⍝ start reading
                    fifoIn.OpenRead
                    fifoOut.OpenWrite
                :EndIf

                ⍝ connection established
                ready←1

                ⍝ send out the PID message
                Msgs.PID USend ⍕os.GetPID

                ⍝ handle incoming messages
                :Repeat
                    ok msg data←URecv 0
                    :If ~ok ⋄ :Leave ⋄ :EndIf
                    msg HandleMsg data
                :Until ~ready
            ∇

            ⍝ Send Unicode message
            ∇ mtype USend data
                mtype Send 'UTF-8' ⎕UCS data
            ∇

            ⍝ Send message (as raw data)
            ∇ mtype Send data;send;sizefield;rc
                'Inactive instance' ⎕SIGNAL BROKEN when ~ready

                ⍝ construct data to  send

                ⍝ vectorize argument if scalar
                :If ⍬≡⍴data ⋄ data←,data ⋄ :EndIf

                ⍝ error handling
                'mtype must fit in a byte' ⎕SIGNAL 11 when mtype≠0⌈255⌊mtype
                'data size too large' ⎕SIGNAL 10 when (≢data)≥2*32
                'message must be byte vector' ⎕SIGNAL 11 when 0≠⍬⍴0⍴data
                'message must be byte vector' ⎕SIGNAL 11 when 1≠⍴⍴data

                sizefield←(4/256)⊤≢data
                ⍝ send the message
                :Trap 999
                    fifoOut.Write (mtype,sizefield,data)
                :Else
                    ready←0
                :EndTrap
            ∇

            ⍝ Send a message and expect a response
            ∇ (type data)←response_type ExpectAfterSending (msgtype msgdata);tS
                ⍝ we don't want interrupts in here
                tS←2503⌶1

                msgtype USend msgdata
                (type data)←Expect response_type

                {}2503⌶tS
            ∇

            ⍝ Expect a message
            ⍝ Returns (type,data) for a message.
            ∇ (type data)←Expect msgtype;ok
                :Repeat
                    ok type data←URecv 0

                    :If ~ok
                        ready←0
                        ⎕SIGNAL⊂('EN'BROKEN)('Message' 'Connection broken.')
                        →out
                    :EndIf

                    ⍝ if this is the expected message or an error message,
                    ⍝ send it on
                    :If type∊msgtype Msgs.ERR
                        :Leave
                    :Else
                        ⍝ this is some other message that needs to be handled first
                        :Trap 1000
                            ⍝ if we are interrupted during HandleMsg, that means
                            ⍝ the APL side has been interrupted, and we need to tell
                            ⍝ Python this
                            type HandleMsg data
                        :Else
                            Msgs.ERR USend #.Py.MSGErr 'Interrupt'
                        :EndTrap
                    :EndIf
                :EndRepeat
                out:

            ∇

            ⍝ Receive Unicode message
            ∇ (success mtype recv)←URecv async;s;m;r
                s m r←Recv async
                (success mtype recv)←s m ('UTF-8' (⎕UCS⍣(s>0)) r)
            ∇

            ⍝ Receive message. Will also signal Python on interrupt, if the Python is ours
            ⍝ Message fmt: X L L L L Data
            ∇ (success mtype recv)←Recv m;header;body;len;tS;state
                'Inactive instance' ⎕SIGNAL BROKEN when ~ready

                tS←2503⌶1 ⍝ no traps allowed

                :Trap 999
                    :Trap 998 1000 ⍝ IPC signals 998 if interrupted by the OS
                        ⍝ read five bytes to get the message header


                        readhdr:
                        ⍝ explicitly allow traps in here unless they are turned off
                        {}2503⌶noInterrupts
                        header←fifoIn.Read 5

                        readbdy:
                        {}2503⌶1

                        ⍝ Don't allow interrupts while reading the body
                        m←⊃header
                        len←256⊥1↓header

                        ⍝ read the body
                        body←fifoIn.Read len


                        (success mtype recv)←1 m body
                        →out
                    :Else
                        {}2503⌶1

                        ⍝ interrupt
                        ⍝ signal python
                        :If signalPython
                            os.Interrupt pid
                        :EndIf

                        ⍝ if we don't have the header yet, read it
                        →(0=⎕NC'header')/readhdr

                        ⍝ if we don't have the body yet, read that
                        →(0=⎕NC'body')/readbdy
                    :EndTrap
                :Else
                    ⍝ error
                    state←0
                    (success mtype recv)←0 0 ⍬
                    →out
                :EndTrap

                out:
                ⍝ restore thread state to what it was before
                {}2503⌶tS
            ∇
        :EndSection

        ⍝ Handle an incoming message
        ∇ mtype HandleMsg mdata;in;expr;args;ns;rslt;lines;tS
            :Trap 1000
                {}2503⌶tS←2503⌶1 ⍝ query thread state

                :Select mtype

                    ⍝ 'OK' message
                    ⍝ There is no real reason for this to come in, but let's
                    ⍝ acknowledge it.
                :Case Msgs.OK
                    Msgs.OK USend mdata

                    ⍝ 'STOP' message
                :Case Msgs.STOP
                    Stop

                    ⍝ 'REPR' message
                :Case Msgs.REPR
                    :Trap 0
                        Msgs.REPRRET USend ⍕pyaplns⍎mdata
                    :Else
                        Msgs.ERR USend #.Py.DMXErr ⎕DMX
                    :EndTrap

                    ⍝ 'EXEC' message
                :Case Msgs.EXEC

                    ⍝ split the message by newlines
                    pyaplns.∆∆∆∆∆←(~mdata∊⎕ucs 10 13)⊆mdata


                    :Trap 0
                        rslt←pyaplns⍎'⎕FX ∆∆∆∆∆'
                        :If ''≡0↑rslt
                            Msgs.OK USend rslt
                        :Else
                            Msgs.ERR USend #.Py.MSGErr 'Error on line ',⍕rslt
                        :EndIf
                    :Else
                        Msgs.ERR USend #.Py.DMXErr ⎕DMX
                    :EndTrap


                    ⍝ 'EVAL' message
                :Case Msgs.EVAL
                    :Trap 0

                        in←deserialize mdata

                        ⍝check message format
                        :If 2≠≢in
                            Msgs.ERR USend #.Py.MSGErr 'Malformed EVAL message'
                            :Return
                        :EndIf

                        expr args←in

                        ⍝namespace to run the expr in

                        ⍝ expose the arguments and this class for communication with Python
                        pyaplns.∆←args
                        pyaplns.py←⎕THIS 

                        ⍝ we explicitly _do_ want to be able to be interrupted while exec'ing

                        tS←2503⌶noInterrupts

                        ⍝ send the result back, if no result then []
                        rslt←pyaplns.{85::⍬ ⋄ 0(85⌶)⍵}expr                   

                        {}2503⌶tS

                        Msgs.EVALRET USend serialize rslt
                    :Else
                        {}2503⌶tS
                        Msgs.ERR USend #.Py.DMXErr ⎕DMX

                    :EndTrap

                    ⍝ Debug serialization round trip
                :Case Msgs.DBGSerializationRoundTrip
                    :Trap 0
                        mtype USend serialize deserialize mdata
                    :Else
                        Msgs.ERR USend #.Py.DMXErr ⎕DMX
                    :EndTrap

                :Else
                    Msgs.ERR USend 'Message not implemented #',⍕mtype
                :EndSelect

            :Else
                ⍝ restore thread state
                {}2503⌶tS
                Msgs.ERR USend #.Py.MSGErr 'Interrupt'
            :EndTrap 
        ∇
        ⍝ debug function (eval/repr)
        ∇ str←Repr code;mtype;recv
            :Access Public

            ⍝receive message
            mtype recv←Msgs.REPRRET ExpectAfterSending (MSG.REPR code)

            :If mtype≠Msgs.REPRRET
                ⎕←'Received non-repr message: ' mtype recv
                →0
            :EndIf

            str←recv
        ∇

        ⍝ Import a Python module and return it as an APL object
        ∇ {obj}←Import module
            :Access Public
            :Trap 0 1000
                Exec'import ',module
                obj←Eval module
            :Else ⋄ ⎕SIGNAL⊂('EN'(⎕DMX.EN))('Message'(⎕DMX.Message))
            :EndTrap
        ∇

        ⍝ Import from
        ∇ {obj}←ImportFrom (module child)
            :Access Public
            :Trap 0 1000
                Exec'from ',module,' import ',child
                obj←Eval child
            :Else ⋄ ⎕SIGNAL⊂('EN'(⎕DMX.EN))('Message'(⎕DMX.Message))
            :EndTrap
        ∇

        ⍝ expose a Python function as a monadic APL "function" (using a namespace)
        ⍝ the argument is *args. The optional left argument is a boolean vector
        ⍝ specifying for each argument whether or not it should be translated
        ⍝ (default: yes)
        ⍝ I wanted to use operators for this at first, but apparently you can't have
        ⍝ public operators in classes.
        ∇ ret←PyFn pyfn
            :Access Public


            ret←⎕NS''
            ret.py←⎕THIS
            ret.fname←pyfn

            ⍝ call function with arguments as vector
            ⍝ the optional left argument is a boolean vector
            ⍝ describing for each argument whether it should be converted
            ret.CallVec←{
                ⍺←(≢,⍵)/1
                ('(',fname,')(',(1↓∊',',[1.5]'⍞⎕'[1+⍺]),')') py.Eval ,⍵
            }

            ⍝ call the function with APL left and right arguments
            ⍝ only works for monadic or dyadic functions
            ret.Call←{⍺←⊂ ⋄ CallVec ⍺ ⍵}
        ∇

        ⍝ evaluate Python code w/arguments
        ∇ ret←{expr} Eval args;msg;mtype;recv;nargs;tS
            :Access Public

            ⍝ We don't want to be interrupted, except in parts where it is explicitly
            ⍝ allowed (called functions will 2503⌶0 in places)
            tS←2503⌶1

            ⍝ support both the " python Eval args " syntax, as the
            ⍝ "Eval python args" syntax.
            :If 0=⎕NC'expr'
                ⍝ only one argument
                :If 1=≡args
                    ⍝ argument is simple, assume an expression w/o arguments
                    expr←args
                    args←⍬
                :Else
                    ⍝ argument is complex, assume an expression followed by
                    ⍝ arguments
                    expr←⊃args
                    args←1↓args
                :EndIf
            :EndIf

            expr←,expr
            args←,args
            msg←serialize(expr args)

            mtype recv←Msgs.EVALRET ExpectAfterSending (Msgs.EVAL msg)

            :If mtype=Msgs.EVALRET
                ret←deserialize recv
                →out
            :EndIf

            ⍝ catch error message
            :If mtype=Msgs.ERR
                lastError←recv
                ⎕SIGNAL⊂('EN'PYERR)('Message' recv)
                →out
            :EndIf

            →err
            out:
            {}2503⌶tS
            :Return

            err:
            ⍝ this shouldn't happen and is an internal bug
            ('Unexpected: ',⍕mtype recv)⎕SIGNAL BUGERR
        ∇

        ⍝ execute Python code
        ∇ Exec code;mtype;recv;tS
            :Access Public

            ⍝ We don't want to be interrupted, except in parts where it is explicitly
            ⍝ allowed (called functions will 2503⌶0 in places)
            tS←2503⌶1

            mtype recv←Msgs.OK ExpectAfterSending (Msgs.EXEC code)

            :If mtype=Msgs.OK
                →out
            :ElseIf mtype=Msgs.ERR
                lastError←recv
                ⎕SIGNAL⊂('EN'PYERR)('Message' recv)
                →out
            :EndIf

            →err
            out:
            {}2503⌶tS
            :Return

            err:
            ⍝ this shouldn't happen and is an internal bug
            ('Unexpected: ',⍕mtype recv)⎕SIGNAL BUGERR
        ∇

        ⍝ Assign a value to a Python variable
        ∇ var Set val;vname;tS
            :Access Public
            tS←2503⌶1
            vname←'__temp',⍕?1e10
            {}'globals().update({⎕:⎕})' Eval vname val
            Exec var,'=',vname
            Exec 'del ',vname
            {}2503⌶tS
        ∇ 

        ⍝ Assign a value to a variable (raw)
        ∇ var SetRaw val;vname;tS
            :Access Public
            tS←2503⌶1
            vname←'__temp',⍕?1e10
            {}'globals().update({⎕:⎕})' Eval vname val
            Exec var,'=',vname
            Exec 'del ',vname
            {}2503⌶tS
        ∇

        ⍝ Initialization common to the server and the client
        ∇ InitCommon
            pyaplns←⎕NS''
            objectStore←⎕NEW #.Py.ObjectStore

            ⍝ check OS
            :If ∨/'Windows'⍷⊃#.⎕WG'APLVersion'
                os←⎕NEW #.Py.WindowsInterface
            :Else
                os←⎕NEW UnixInterface
            :EndIf                   

            #.IPC.Init

        ∇

        ⍝ Client initialization routine
        ∇ InitClient (clin clout)
            InitCommon
            signalPython←0
            RunClient clin clout
        ∇

        ⍝ Initialization routine
        ∇ InitServer (startAsync argfmt forceTCP);ok;tries;code;clt;success;_;msg;srvport;piducs;spath;if;of
            InitCommon
            signalPython←1

            ⍝ If we're on Windows, always use TCP
            :If ∨/'Windows'⍷⊃#.⎕WG'APLVersion'
                forceTCP←1
            :EndIf 

            ⍝ make input and output FIFOs
            :If forceTCP
                #.IPC.TCP.Init
                fifoIn ← ⎕NEW #.IPC.TCP.Connection
                fifoOut ← fifoIn ⍝ TCP connection is bidirectional
                of←'TCP'
                if←⍕fifoOut.StartServer  
            :Else
                fifoIn ← ⎕NEW #.IPC.OS.FIFO
                fifoOut ← ⎕NEW #.IPC.OS.FIFO  
                of←fifoOut.Name
                if←fifoIn.Name
            :EndIf 

            :If debugMsg
                ⎕←'(1) ',of
                ⎕←'(2) ',if
            :EndIf


            ⍝ start Python
            spath←(os.GetPath #.Py.ScriptPath),filename

            :If ~attachToExistingPython
                ⍝ NOTE: APL's 'out' is Python's 'in' and vice versa, of course
                pypath os.StartPython argfmt spath of if majorVersion
            :EndIf

            ready←1

            :If debugMsg
                ⎕←'Waiting for Python to open its pipe'
            :EndIf

            ⍝ Python client should now send PID

            :If forceTCP
                fifoOut.AcceptConnection
            :Else
                fifoOut.OpenWrite
                fifoIn.OpenRead
            :EndIf

            :If debugMsg
                ⎕←'Done.'
            :EndIf

            msg piducs←Expect Msgs.PID
            success pid←⎕VFI piducs
            :If ~success
                ⎕←'PID not a number'
                →ready←0
            :EndIf

            :If debugMsg
                ⎕←'OK! pid=',pid
            :EndIf
        ∇

        ∇ construct
            :Access Public Instance
            :Implements Constructor

            InitServer 0 '' 0
        ∇

        ⍝ param constructor 
        ⍝ this takes a (param value) vector of vectors
        ∇ paramConstruct param;dC;par;val;clin;clout;startAsync;argfmt;forceTCP
            :Access Public Instance
            :Implements Constructor

            ⍝ if only one parameter, enclose the vector
            param←⊂⍣(2=|≡param)⊢param

            argfmt←''
            startAsync←0
            clin clout←'' '' 
            forceTCP←0
            :For (par val) :In param
                :Select par
                    ⍝ debug parameter
                :Case'Debug' ⋄ debugMsg←attachToExistingPython←1
                    ⍝ pass in the path to the python interpreter explicitly
                :Case'PyPath' ⋄ pypath←val 
                    ⍝ pass in a different argument format if necessary
                :Case 'ArgFmt' ⋄ argfmt←val
                    ⍝ construct a client instead of a server
                :Case 'Client' ⋄ clin clout←val
                    ⍝ set the Python major version
                :Case 'Version' ⋄ majorVersion←val
                    ⍝ wait to attach to existing python
                :Case 'Attach' ⋄ attachToExistingPython←1
                    ⍝ start the asynchronous thread 
                :Case 'ForceTCP' ⋄ forceTCP←val
                    ⍝ disallow interrupts
                :Case 'NoInterrupts' ⋄ noInterrupts←val 
                    ⍝ disable display forms
                :Case 'NoDF' ⋄ noDF←val
                :EndSelect

            :EndFor

            :If 0=≢clin
                InitServer startAsync argfmt forceTCP
            :Else
                InitClient clin clout
            :EndIf
        ∇

        ∇ Stop
            :Access Public Instance
            ⍝ send a Stop message, we don't care if it succeeds

            :Trap 0 ⋄ Msgs.STOP USend 'STOP' ⋄ :EndTrap

            ⍝ give Python a small time to respond
            ⎕DL ÷4

            ⍝ close the file sockets
            fifoIn.Close
            fifoOut.Close

            :If signalPython

                :If ~attachToExistingPython
                    ⍝ try to kill the process we started, in case it has not properly exited    
                    os.Kill pid      
                :EndIf

            :EndIf

            ⍝ we are no longer ready for commands.
            ready←0
        ∇

        ∇ destruct
            :Implements Destructor
            Stop
        ∇

    :EndClass

:EndNamespace
