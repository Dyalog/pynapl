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

    ⍝ Start an APL slave and connect to the server at the given port
    ∇StartAPLSlave port;py
        py←⎕NEW Py ('Client' port)
    ∇

    :Class JSONSerializer

        ⍝ deserialize
        ∇ r←deserialize json
            :Access Public Shared
            r←decode ⎕JSON json
        ∇

        ∇ r←decode obj
            :Access Public Shared

            :If 9.1≠⎕NC⊂'obj'
                ⍝ automatically decoded by ⎕JSON
                r←obj
                :Return
            :EndIf

            :If 0≠⎕NC'obj.ns'
                ⍝ an encoded namespace
                r←decodeNS obj.ns
                :Return
            :EndIf

            ⍝ if not a simple object or a namespace,
            ⍝ it must then be an array

            :If (0=≢obj.d)∧0≠⎕NC'obj.t'
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
                r←obj.r⍴decode¨⊃¨obj.d
            :EndIf
        ∇

        ∇ r←decodeNS ns;child;children;dec
            r←⎕NS''

            children←ns.⎕NL-2 9

            :For child :In children
                dec←decode ns.⍎child
                child r.{⍎⍺,'←⍵'}dec
            :EndFor
        ∇

        ⍝ serialize
        ∇ r←serialize obj;enc;ns
            :Access Public Shared
            enc←encode obj
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
            :Access Public Shared

            :If 0=⎕NC'taboo' ⋄ taboo←⍬ ⋄ :EndIf

            :If ~(⎕NC⊂'obj')∊2.1 2.2 9.1
                ⎕SIGNAL⊂('EN' 6)('Message' 'Only values and namespaces containing values can be serialized.')
            :EndIf

            :If 0=≡obj
                ⍝ The object is simple, return it

                ⍝ if it is a namespace, it needs to be encapsulated
                r←taboo encapsulate⍣(9=⊃⎕NC'obj')⊢obj
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
            :Access Public Shared

            :If 0=⎕NC'taboo' ⋄ taboo←⍬ ⋄ :EndIf

            :If obj∊taboo ⋄ r←⍬ ⋄ :EndIf

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

        ∇ {py} StartPython (program srvport);cmd;pypath
            :Access Public Shared
            :If 2=⎕NC'py'
            :andif 0≠≢py
                ⍝use given path
                pypath←py
            :else
                ⍝find python on path
                :Trap 11
                    pypath←⊃⎕SH'which python'
                :Else
                    ⎕SIGNAL⊂('EN'999)('Message' 'Cannot find Python on the path.')
                :EndTrap
            :endif
            ⎕SH pypath,' ',program,' ',(⍕srvport),' >/dev/null &'

        ∇

        ∇ Kill pid
            :Access Public Shared
            ⎕SH 'kill ', ⍕pid
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

        ∇ {py} StartPython (program srvport);pypath
            :Access Public Instance
            ⍝⎕USING←'System.Diagnostics,System.dll'
            ⍝⎕USING,←⊂'Microsoft.Win32,mscorlib.dll' 

            :If 2=⎕NC'py' 
            :andIf 0≠≢py
                ⍝ use given path
                pypath←py
            :ElseIf 0=≢pypath←FindPythonInRegistry 
                ⍝ can't find it in registry either
                ⎕SIGNAL⊂('EN'999)('Message' 'Cannot find Python in registry.')
            :EndIf


            :Trap 90
                pyProcess←⎕NEW Process
                pyProcess.StartInfo.FileName←pypath
                pyProcess.StartInfo.Arguments←program,' ',⍕srvport  
                pyProcess.StartInfo.RedirectStandardOutput←1
                pyProcess.StartInfo.RedirectStandardError←1 
                pyProcess.StartInfo.UseShellExecute←0
                pyProcess.StartInfo.CreateNoWindow←1  
                {}pyProcess.Start ⍬
            :Else
                ⎕SIGNAL⊂('EN'999)('Message' 'Cannot start Python')
            :EndTrap
        ∇

        ∇ path←FindPythonInRegistry;rk;rka;rkb;comp;ver
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
            comp←⊃rk.GetSubKeyNames
            rk←rk.OpenSubKey(comp 0)          ⋄ →('[Null]'≡⍕rk)/fail
            ver←⊃{('2'=⊃¨⍵)/⍵}rk.GetSubKeyNames ⍝ version 2.x
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
            :Trap 90
                ⍝ The process is supposed to exit on its own, so there's a good chance
                ⍝ this will give an exception, thus the trap.
                pyProcess.Kill ⍬                             
            :EndTrap
        ∇           



    :EndClass

    ⍝ Connect to 
    :Class Py

        when←/⍨

        ⍝ errors
        :Field Private PYERR←11   ⍝ error raised when Python returns an error
        :Field Private BROKEN←990 ⍝ error raised when the object is not in an usable state
        :Field Private BUGERR←15  ⍝ error raised when the cause is an internal bug

        :Field Private ready←0
        :Field Private serverSocket←⍬
        :Field Private connSocket←⍬
        :Field Private pid←¯1
        :Field Private os

        :Field Private lastError←''

        :Field Private filename←'APLBridgeSlave.py'

        :Field Private pypath←''

        ⍝ this holds the namespace in which APL code sent from the Python side
        ⍝ will be evaluated.
        :Field Private pyaplns←⍬

        ⍝ the debug constructor will set this, so the program will wait
        ⍝ to connect to an external APLBridgeSlave.py rather than launch
        ⍝ one.
        :Field Private debugConnect←0

        ∇ r←GetLastError
            :Access Public
            r←lastError
        ∇

        ⍝ JSON serialization/deserialization
        :Section JSON serialization/deserialization
            ⍝ Check whether an array is serializable
            serializable←{
                ⍝ for an array to be serializable, each of its elements
                ⍝ when assigned to a variable must result in ⎕NC=2
                ⊃2∧.={w←⍵ ⋄ ⎕NC'w'}¨∊⍵
            }

            ⍝ Serialize a (possibly nested) array
            serialize←{#.Py.JSONSerializer.serialize ⍵}

            ⍝ Deserialize a (possibly nested) array
            deserialize←{#.Py.JSONSerializer.deserialize ⍵}

            :Section JSON serialization debug code
                ⍝ Send an array through the serialization code on both sides
                ⍝ and see what comes back. No other mangling is done, the Python
                ⍝ side just gets an APLArray.
                ∇out←TestArrayRoundTrip in;sin;sout;msg
                    :Access Public
                    sin ← serialize in

                    Msgs.DBGSerializationRoundTrip USend sin
                    msg sout←Expect Msgs.DBGSerializationRoundTrip

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

            :Field Private attempts←10
            :Field Private curdata←⍬
            :Field Private curlen←¯1
            :Field Private curtype←¯1
            :Field Private reading←0

            ⍝ Run a client on a given a port
            ∇ RunClient port;rv;ok;msg;data

                rv←#.DRC.Clt '' 'localhost' port 'Raw'
                :If 0=⊃rv
                    ⍝ connection established
                    connSocket←2⊃rv
                    ready←1

                    ⍝ send out the PID message
                    Msgs.PID USend ⍕os.GetPID

                    ⍝ handle incoming messages
                    :Repeat
                        ok msg data←URecv
                        :If ~ok ⋄ :Leave ⋄ :EndIf
                        msg HandleMsg data
                    :Until ~ready
                :Else
                    ⎕←rv
                    'Connection to Python server failed.'⎕SIGNAL BROKEN
                :EndIf

            ∇
            ⍝ Find an open port and start a server on it
            ∇ port←StartServer;tryPort;rv
                :For tryPort :In ⌽⍳50000 ⍝ 65535
                    rv←#.DRC.Srv '' 'localhost' tryPort 'Raw'
                    :If 0=⊃rv
                        port←tryPort
                        serverSocket←2⊃rv

                        ⍝ debug output
                        :If debugConnect
                            ⎕←'Started server ',serverSocket,' on port ',port
                        :EndIf

                        :Return
                    :EndIf
                :EndFor

                ⎕SIGNAL⊂('EN'BROKEN)('Message' 'Failed to start server')
            ∇

            ⍝ Wait for connection, set connSocket if connected
            ∇ AcceptConnection;rc;rval
                :Repeat
                    rc←⊃rval←#.DRC.Wait serverSocket
                    :If rc=0
                        connSocket←2⊃rval
                        :Leave
                    :ElseIf rc=100
                        ⍝ Timeout
                        ⎕←'Timeout, retrying'
                    :Else
                        ⍝ Error
                        ⎕SIGNAL⊂('EN'BROKEN)('Message' (⍕'Socket error' rval))
                        :Leave
                    :EndIf            
                :EndRepeat
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
                rc←#.DRC.Send connSocket (mtype,sizefield,data)
                :If 0≠⊃rc
                    ('Socket error ',⍕rc) ⎕SIGNAL BROKEN
                :EndIf
            ∇

            ⍝ Expect a message
            ⍝ Returns (type,data) for a message.
            ∇ (type data)←Expect msgtype;ok
                ⍝ TODO: this will handle incoming messages arising from
                ⍝ a sent message if applicable

                :Repeat
                    ok type data←URecv

                    :If ~ok
                        ready←0
                        ⎕SIGNAL⊂('EN'BROKEN)('Message' 'Connection broken.')
                        :Return
                    :EndIf

                    ⍝ if this is the expected message or an error message,
                    ⍝ send it on
                    :If type∊msgtype Msgs.ERR
                        :Leave
                    :Else
                        ⍝ this is some other message that needs to be handled
                        type HandleMsg data
                        ⍝ afterwards we need to start listening for our message
                        ⍝ again
                    :EndIf
                :EndRepeat
            ∇

            ⍝ Receive Unicode message
            ∇ (success mtype recv)←URecv;s;m;r
                s m r←Recv
                (success mtype recv)←s m ('UTF-8' (⎕UCS⍣s) r)
            ∇

            ⍝ Receive message.
            ⍝ Message fmt: X L L L L Data
            ∇ (success mtype recv)←Recv;done;wait_ret;rc;obj;event;sdata;tmp
                'Inactive instance' ⎕SIGNAL BROKEN when ~ready


                :Repeat
                    :If (~reading) ∧ 5≤≢curdata
                        ⍝ we're not in a message and have data available for the header
                        curtype←⊃curdata ⍝ first byte is the type
                        curlen←256⊥4↑1↓curdata ⍝ next 4 bytes are the length
                        curdata↓⍨←5
                        ⍝ we are now reading the message body
                        reading←1
                    :ElseIf reading ∧ curlen ≤ ≢curdata
                        ⍝ we're in a message and have enough data to complete it
                        (success mtype recv)←1 curtype (curlen↑curdata)
                        curdata ↓⍨← curlen
                        ⍝ therefore, we are no longer reading a message
                        reading←0
                        :Return
                    :Else
                        ⍝ we don't currently have enough data for what we need
                        ⍝ (either a message or a header), so we need to read more

                        :Repeat
                            rc←⊃wait_ret←#.DRC.Wait connSocket

                            :If rc=0 ⍝ success
                                rc obj event sdata←wait_ret
                                connSocket←obj
                                :Select event
                                :Case 'Block' ⍝ we have data
                                    curdata ,← sdata
                                    :Leave
                                :CaseList 'BlockLast' 'Error'
                                    ⍝ an error has occured
                                    →error
                                :EndSelect
                            :ElseIf rc=100 ⍝ timeout
                                {}⎕DL 0.5 ⍝ wait half a second and try again
                            :Else ⍝ not a timeout and not success → error
                                →error
                            :EndIf
                        :EndRepeat
                    :EndIf



                :EndRepeat

                :Return

                error:
                (success mtype recv)←0 ¯1 sdata
                ready←0

            ∇
        :EndSection





        ⍝ Handle an incoming message
        ∇ mtype HandleMsg mdata;in;expr;args;ns;rslt;lines
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
                    Msgs.ERR USend ⍕⎕DMX.(EM Message)
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
                        Msgs.ERR USend 'Error on line ',⍕rslt
                    :EndIf
                :Else
                    Msgs.ERR USend ⍕⎕DMX.(EM Message)
                :EndTrap


                ⍝ 'EVAL' message
            :Case Msgs.EVAL
                :Trap 0

                    in←deserialize mdata

                    ⍝check message format
                    :If 2≠≢in
                        Msgs.ERR USend 'Malformed EVAL message'
                        :Return
                    :EndIf

                    expr args←in

                    ⍝namespace to run the expr in

                    ⍝ expose the arguments and this class for communication with Python
                    pyaplns.∆←args
                    pyaplns.py←⎕THIS 

                    ⍝ send the result back
                    rslt←pyaplns⍎expr                   

                    Msgs.EVALRET USend serialize rslt
                :Else
                    Msgs.ERR USend ⍕⎕DMX.(EM Message)
                :EndTrap

                ⍝ Debug serialization round trip
            :Case Msgs.DBGSerializationRoundTrip
                :Trap 0
                    mtype USend serialize deserialize mdata
                :Else
                    Msgs.ERR USend ⍕⎕DMX.(EM Message)
                :EndTrap

            :Else
                Msgs.ERR USend 'Message not implemented #',⍕mtype
            :EndSelect
        ∇
        ⍝ debug function (eval/repr)
        ∇ str←Repr code;mtype;recv
            :Access Public

            ⍝ send the message
            Msgs.REPR USend code

            ⍝receive message
            mtype recv←Expect Msgs.REPRRET

            :If mtype≠Msgs.REPRRET
                ⎕←'Received non-repr message: ' mtype recv
                →0
            :EndIf

            str←recv
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
                (fname,'(',(1↓∊',',[1.5]'⍞⎕'[1+⍺]),')') py.Eval ,⍵   
            }

            ⍝ call the function with APL left and right arguments
            ⍝ only works for monadic or dyadic functions
            ret.Call←{⍺←⊂ ⋄ CallVec ⍺ ⍵}
        ∇

        ⍝ evaluate Python code w/arguments
        ∇ ret←expr Eval args;msg;mtype;recv;nargs
            :Access Public

            expr←,expr
            args←,args
            msg←serialize(expr args)

            Msgs.EVAL USend msg

            mtype recv←Expect Msgs.EVALRET

            :If mtype=Msgs.EVALRET
                ret←deserialize recv
                :Return
            :EndIf

            ⍝ catch error message
            :If mtype=Msgs.ERR
                lastError←recv
                ⎕SIGNAL⊂('EN'PYERR)('Message' recv)
                :Return
            :EndIf

            ⍝ this shouldn't happen and is an internal bug
            ('Unexpected: ',⍕mtype recv)⎕SIGNAL BUGERR
        ∇

        ⍝ execute Python code
        ∇ Exec code;mtype;recv
            :Access Public
            Msgs.EXEC USend code

            mtype recv←Expect Msgs.OK

            :If mtype=Msgs.OK
                :Return
            :ElseIf mtype=Msgs.ERR
                lastError←recv
                ⎕SIGNAL⊂('EN'PYERR)('Message' recv)
                :Return
            :EndIf

            ⍝ this shouldn't happen and is an internal bug
            ('Unexpected: ',⍕mtype recv)⎕SIGNAL BUGERR
        ∇

        ⍝ Initialization common to the server and the client
        ∇ InitCommon
            reading←0 ⋄ curlen←¯1 ⋄ curdata←'' ⋄ curtype←¯1
            pyaplns←⎕NS''

            ⍝ check OS
            :If ∨/'Windows'⍷⊃#.⎕WG'APLVersion'
                os←⎕NEW #.Py.WindowsInterface
            :Else
                os←⎕NEW UnixInterface
            :EndIf

            ⍝ load Conga
            :If 0=⎕NC'#.DRC'
                'DRC'#.⎕CY 'conga.dws'
            :EndIf

            :If 0≠⊃#.DRC.Init ''
                'Conga is unavailable.' ⎕SIGNAL BROKEN
            :EndIf          
        ∇

        ⍝ Client initialization routine
        ∇ InitClient port
            InitCommon
            RunClient port
        ∇

        ⍝ Initialization routine
        ∇ InitServer;ok;tries;code;clt;success;_;msg;srvport;piducs;spath
            InitCommon

            ⍝ Attempt to start a server
            srvport←StartServer

            ⍝ start Python
            spath←(os.GetPath #.Py.ScriptPath),filename

            :If ~debugConnect
                pypath os.StartPython spath srvport
            :EndIf

            ready←1

            ⍝ Python client should now send PID
            AcceptConnection

            msg piducs←Expect Msgs.PID
            success pid←⎕VFI piducs
            :If ~success
                ⎕←'PID not a number'
                →ready←0
            :EndIf

            :If debugConnect
                ⎕←'OK! pid=',pid
            :EndIf

        ∇

        ∇ construct
            :Access Public Instance
            :Implements Constructor

            InitServer
        ∇

        ⍝ param constructor 
        ⍝ this takes a (param value) vector of vectors
        ∇ paramConstruct param;dC;par;val;clport
            :Access Public Instance
            :Implements Constructor

            ⍝ if only one parameter, enclose the vector
            param←⊂⍣(2=|≡param)⊢param

            clport←0
            :For (par val) :In param
                :Select par
                    ⍝ debug parameter
                :Case'Debug' ⋄ debugConnect←val
                    ⍝ pass in the path to the python interpreter explicitly
                :Case'PyPath' ⋄ pypath←val 
                    ⍝ construct a client instead of a server
                :Case 'Client' ⋄ clport←val

                :EndSelect

            :EndFor

            :If 0=clport
                InitServer
            :Else
                InitClient clport
            :EndIf
        ∇

        ∇ Stop
            :Access Public Instance
            ⍝ send a Stop message, we don't care if it succeeds
            :Trap 0 ⋄ Msgs.STOP USend 'STOP' ⋄ :EndTrap

            :If 0≠≢serverSocket
                ⍝ This is a server, so do the necessary clean-up

                {}⎕DL ÷4 ⍝give the Python instance a small time to finish up properly

                ⍝ shut down the server 
                {}#.DRC.Close serverSocket 

                :If ~debugConnect
                    ⍝ try to kill the process we started, in case it has not properly exited    
                    os.Kill pid      
                :EndIf
            :Else
                ⍝ close the client socket
                {}#.DRC.Close connSocket
            :EndIF

            ⍝ we are no longer ready for commands
            ready←0
        ∇

        ∇ destruct
            :Implements Destructor
            Stop
        ∇


    :EndClass














:EndNamespace
