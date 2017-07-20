:Namespace Py
    ⎕IO ⎕ML←1




    ⍝ Retrieve the path from the namespace
    ∇r←ScriptPath
        r←SALT_Data.SourceFile
    ∇

    :Class UnixInterface
        ⍝ Functions to interface with Unix OSes

        ∇ r←GetPath fname
            :Access Public Shared
            r←(⌽∨\⌽'/'=fname)/fname
        ∇

        ∇ StartPython (program srvport);cmd
            :Access Public Shared
            ⎕SH 'python ',program,' ',(⍕srvport),'>/dev/null &'
        ∇

        ∇ Kill pid
            :Access Public Shared
            ⎕SH 'kill ', ⍕pid
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
        :Field Private serverSocket←'SPy'
        :Field Private connSocket←⍬
        :Field Private pid←¯1
        :Field Private os

        :Field Private lastError←''

        :Field Private filename←'APLBridgeSlave.py'

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

            ⍝ Find an open port and start a server on it
            ∇ port←StartServer;tryPort;rv
                :For tryPort :In ⌽⍳65535
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
                    ns←⎕NS''
                    ⍝ expose the arguments and this class for communication with Python
                    ns.∆←args
                    ns.py←⎕THIS 

                    ⍝ send the result back
                    rslt←ns⍎expr                   

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

        ⍝ Initialization routine
        ∇ Init;ok;tries;code;clt;success;_;msg;srvport;piducs
            reading←0 ⋄ curlen←¯1 ⋄ curdata←'' ⋄ curtype←¯1

            ⍝ the OS is assumed to be Unix for now
            os←⎕NEW UnixInterface

            ⍝ load Conga
            :If 0=⎕NC'#.DRC'
                'DRC'#.⎕CY 'conga.dws'
            :EndIf

            :If 0≠⊃#.DRC.Init ''
                'Conga is unavailable.' ⎕SIGNAL BROKEN
            :EndIf

            ⍝ Attempt to start a server
            srvport←StartServer

            ⍝ start Python
            pypath←(os.GetPath #.Py.ScriptPath),filename

            :If ~debugConnect
                os.StartPython pypath srvport
            :EndIf

            ready←1

            ⍝ Python client should now send PID
            ⎕←'Waiting for connection... '

            AcceptConnection

            msg piducs←⎕←Expect Msgs.PID

            success pid←⎕VFI piducs
            :If ~success
                ⎕←'PID not a number'
                →ready←0
            :EndIf

            ⎕←'OK! pid='pid     

        ∇

        ∇ construct
            :Access Public Instance
            :Implements Constructor

            Init
        ∇

        ⍝ debug constructor
        ∇ debugConstruct dbgparam;dC
            :Access Public Instance
            :Implements Constructor

            :If 'DEBUG'≡⊃dbgparam
                debugConnect←2⊃dbgparam
            :EndIf

            Init
        ∇

        ∇ Stop
            :Access Public Instance
            ⍝ send a Stop message, we don't care if it succeeds
            ⎕←'Sending STOP'
            :Trap 0 ⋄ Msgs.STOP USend 'STOP' ⋄ :EndTrap

            {}⎕DL ÷4 ⍝give the Python instance a small time to finish up properly

            ⍝ shut down the server 
            {}#.DRC.Close serverSocket 

            ⍝ try to kill the process we started, in case it has not properly exited
            os.Kill pid

            ⍝ we are no longer ready for commands
            ready←0
        ∇

        ∇ destruct
            :Implements Destructor
            Stop
        ∇


    :EndClass














:EndNamespace
