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
            ⎕SH 'python ',program,' ',(⍕srvport),'>/home/marinus/log &'
        ∇

        ∇ Kill pid
            :Access Public Shared
            ⎕SH 'kill ', ⍕pid
        ∇
    :EndClass


    ⍝ Connect to 
    :Class Py

        when←/⍨

        :Field Private ready←0
        :Field Private serverSocket←'SPy'
        :Field Private connSocket←⍬
        :Field Private pid←¯1
        :Field Private os

        :Field Private filename←'APLBridgeSlave.py'

        ⍝ JSON serialization/deserialization
        :Section JSON serialization/deserialization
            ⍝ Check whether an array is serializable
            serializable←{
                ⍝ for an array to be serializable, each of its elements
                ⍝ when assigned to a variable must result in ⎕NC=1
                ⊃2∧.={w←⍵ ⋄ ⎕NC'w'}¨∊⍵
            }

            ⍝ Serialize a (possibly nested) array
            serialize←{
                ~serializable ⍵: 'Array must contain only simple values' ⎕SIGNAL 11
                ⎕JSON {
                    ⍺←0

                    wrap←{
                        n←⎕NS''
                        n.rho←⍴⍵
                        n.data←,⍺⍺¨⍵
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
                    0∨.≥⎕NC'w.data' 'w.rho':⍵

                    w.rho⍴∇¨⊃¨w.data
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
                        ⎕←'Started server ',serverSocket,' on port ',port
                        :Return
                    :EndIf
                :EndFor
                'Failed to start server' ⎕SIGNAL 90   
            ∇

            ⍝ Wait for connection, set connSocket if connected
            ∇ AcceptConnection;rc;rval
                :Repeat
                    rc←⊃rval←#.DRC.Wait serverSocket
                    :If rc=0
                        ⎕←'Connection established'
                        connSocket←2⊃rval
                        ⎕←'Socket: ',connSocket
                        :Leave
                    :ElseIf rc=100
                        ⍝ Timeout
                        ⎕←'Timeout, retrying'
                    :Else
                        ⍝ Error
                        (⍕'Socket error ' rval) ⎕SIGNAL 90
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
                'Inactive instance' ⎕SIGNAL 90 when ~ready

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
                    ('Socket error ',⍕rc) ⎕SIGNAL 90 
                :EndIf
            ∇

            ⍝ Expect a message
            ⍝ Returns (type,data) for a message.
            ∇ (type data)←Expect msgtype;ok
                ⍝ TODO: this will handle incoming messages arising from
                ⍝ a sent message if applicable

                ok type data←URecv

                :If ~ok
                    ⎕←'Connection broken.'
                :EndIf
            ∇

            ⍝ Receive Unicode message
            ∇ (success mtype recv)←URecv;s;m;r
                s m r←Recv
                (success mtype recv)←s m ('UTF-8' (⎕UCS⍣s) r)
            ∇

            ⍝ Receive message.
            ⍝ Message fmt: X L L L L Data
            ∇ (success mtype recv)←Recv;done;wait_ret;rc;obj;event;sdata;tmp
                'Inactive instance' ⎕SIGNAL 90 when ~ready


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
                        →finish
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

                →finish

                error:
                (success mtype recv)←0 ¯1 sdata
                ready←0

                finish:
            ∇
        :EndSection

        ⍝ debug function (eval/repr)
        ∇ str←Repr code;mtype;recv
            :Access Public

            ⍝ send the message
            Msgs.REPR USend code

            ⍝receive message
            mtype recv←Expect Msgs.REPR

            :If mtype≠Msgs.REPR
                ⎕←'Received non-repr message: ' mtype recv
                →0
            :EndIf

            str←recv
        ∇


        ⍝ execute Python code
        ∇ ok←Exec code;mtype;recv
            :Access Public
            Msgs.EXEC USend code

            mtype recv←Expect Msgs.OK

            :If mtype≠Msgs.OK
                ⎕←'Received non-OK message: ' mtype recv
            :EndIf
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

            #.DRC.Init ''

            ⍝ Attempt to start a server
            ⎕←'Starting server'
            srvport←StartServer
            ⎕←'Server at ' srvport


            pypath←(os.GetPath #.Py.ScriptPath),filename

            ⍝ start python
            ⍝os.StartPython pypath srvport

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

        ∇ Stop
            :Access Public Instance
            ⍝ send a Stop message, we don't care if it succeeds
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
