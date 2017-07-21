:Namespace Py
    ⎕IO ⎕ML←1




    ⍝ Retrieve the path from the namespace
    ∇r←ScriptPath
        r←SALT_Data.SourceFile
    ∇

    ⍝ Start an APL slave and connect to the server at the given port
    ∇StartAPLSlave port;py
        ⎕←'Starting...'
        py←⎕NEW Py ('Client' port)
    ∇

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

            ⎕SH pypath,' ',program,' ',(⍕srvport),'>/dev/null &'
        ∇

        ∇ Kill pid
            :Access Public Shared
            ⎕SH 'kill ', ⍕pid
        ∇
    :EndClass     


    :Class WindowsInterface
        ⍝ Functions to interface with Windows using .NET
        ⍝ NOTE: will keep track of the process itself rather than use the pid as in Linux

        :Field Private Instance pyProcess←⍬

        ∇ r←GetPID
            :Access Public Instance
            'Not Implemented' ⎕SIGNAL 15
        ∇

        ∇ r←GetPath fname
            :Access Public Shared
            r←(⌽∨\⌽'\'=fname)/fname
        ∇

        ∇ {py} StartPython (program srvport);pypath
            :Access Public Instance
            ⎕USING←'System.Diagnostics,System.dll'
            ⎕USING,←⊂'Microsoft.Win32,mscorlib.dll' 

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
            serialize←{
                ~serializable ⍵: 'Array must contain only simple values' ⎕SIGNAL 11
                ⎕JSON {
                    ⍺←0

                    wrap←{
                        n←⎕NS''
                        n.r←⍴⍵
                        n.d←,⍺⍺¨⍵

                        ⍝ type_hint: 1 if characters, 0 if numbers
                        ⍝ (python cannot otherwise tell the difference
                        ⍝ if the list is empty)
                        n.t←{
                            dat←n.d

                            ⍝empty array: type is 1 if char prototype
                            0=≢dat: ' '=⊃0↑dat

                            ⍝nested array: type is that of nested array
                            dat←⊃dat
                            9=⎕NC'dat':dat.t

                            ⍝array w/simple value: type of simple value
                            2=⎕NC'dat':' '=⊃0↑dat

                            ('? ⎕NC=',⍕⎕NC'dat' ) ⎕SIGNAL 16
                        }⍬

                        n
                    }

                    0=≡⍵: ⊢wrap⍣(~⍺)⊢⍵
                    1=≡⍵: ⊢wrap ⍵
                    (1∘∇)wrap ⍵
                }⍵
            }

            ⍝ Deserialize a (possibly nested) array
            deserialize←{
                {
                    w←⍵
                    ⍝ if not a JSON object, leave it alone
                    0∨.≥⎕NC'w.d' 'w.r':⍵

                    ⍝ if array is empty and type_hint is
                    ⍝ available, use it to construct an empty array
                    ⍝ of the right type
                    (0=≢w.d)∧0≠⎕NC'w.t':{
                        ⍝ 0 = numbers
                        0=⍵.t: ⍵.r⍴⍬
                        1=⍵.t: ⍵.r⍴''

                        ('Invalid type hint: ',⍕⍵.t)⎕SIGNAL 11 
                    }w

                    ⍝ reconstruct the array as given
                    w.r⍴∇¨⊃¨w.d
                } ⎕JSON ⍵
            }

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
        ∇ mtype HandleMsg mdata;in;expr;args;ns;rslt
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
                    Msgs.REPRRET USend ⍕#⍎mdata
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

        ⍝ evaluate Python code w/arguments
        ∇ ret←expr Eval args;msg;mtype;recv;nargs
            :Access Public

            ⍝ check if argument list length matches # of args in expr

            :If (nargs←+/expr∊'⎕⍞')≠≢args
                (⍕'Expected'nargs'args but got'(≢args))⎕SIGNAL 5
            :EndIf

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
            ⎕←'Sending STOP'
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
