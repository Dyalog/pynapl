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

        ∇ StartPython program;cmd
            :Access Public Shared
            ⎕SH 'python ',pypath,' ',(⍕srvport),'>/home/marinus/log &'
        ∇

        ∇ Kill pid
            :Access Public Shared
            ⎕SH 'kill ', ⍕pid
        ∇
    :EndClass

    :Class Py

        when←/⍨

        :Field Private ready←0
        :Field Private serverSocket←'SPy'
        :Field Private connSocket←⍬
        :Field Private pid←¯1
        :Field Private os

        :Field Private filename←'APLBridgeSlave.py'
        

        :Section Network functions
            :Field Private attempts←10
            
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

                ⎕←'Send message mtype='mtype'data='data

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
                rc←#.DRC.Send connSocket (⎕←mtype,sizefield,data)
                :If 0≠⊃rc
                    ('Socket error ',⍕rc) ⎕SIGNAL 90 
                :EndIf
            ∇
            ⍝ Receive Unicode message
            ∇ (success mtype recv)←URecv;s;m;r
                s m r←Recv
                (success mtype recv)←s m ('UTF-8' (⎕UCS⍣s) r)
            ∇

            ⍝ Receive message.
            ⍝ Message fmt: X L L L L Data
            :Field Private reading←0 
            :Field Private curlen←¯1 
            :Field Private type←¯1 
            :Field Private data←''
            ∇ (success mtype recv)←Recv;done;wait_ret;rc;obj;event;sdata;tmp
                'Inactive instance' ⎕SIGNAL 90 when ~ready


                :Repeat
                    :If (~reading) ∧ 5≤≢data
                        ⍝ we're not in a message and have data available for the header
                        type←⊃data ⍝ first byte is the type
                        curlen←256⊥4↑1↓data ⍝ next 4 bytes are the length
                        data↓⍨←5
                        ⍝ we are now reading the message body
                        reading←1
                    :ElseIf reading ∧ curlen ≤ ≢data
                        ⍝ we're in a message and have enough data to complete it
                        (success mtype recv)←1 type (curlen↑data)
                        data ↓⍨← curlen
                        ⍝ therefore, we are no longer reading a message
                        reading←0
                        →finish
                    :Else
                        ⍝ we don't currently have enough data for what we need
                        ⍝ (either a message or a header), so we need to read more

                        :Repeat
                            rc←⊃⎕←wait_ret←#.DRC.Wait connSocket

                            :If rc=0 ⍝ success
                                rc obj event sdata←wait_ret
                                connSocket←obj
                                :Select event
                                :Case 'Block' ⍝ we have data
                                    data ,← sdata
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
        ∇ str←Eval code;succ;mtype;recv
            :Access Public

            ⍝ send the message
            3 USend code

            ⍝receive message
            succ mtype recv←URecv

            :If ~succ
                ⎕←'Recv failed:' succ mtype recv
                →0
            :EndIf

            :If mtype≠3
                ⎕←'Received non-repr message: ' succ mtype recv
                →0
            :EndIf

            str←recv
        ∇

        ⍝ Initialization routine
        ∇ Init;ok;tries;code;clt;success;_;msg;srvport;piducs
            reading←0 ⋄ curlen←¯1 ⋄ data←'' ⋄ type←¯1

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
            os.StartPython pypath

            ready←1

            ⍝ Python client should now send PID
            ⎕←'Waiting for connection... '

            AcceptConnection

            success msg piducs←⎕←Recv

            :If ~success
                'Connection failure' ⎕SIGNAL 90
            :EndIf

            pid←⊃(//)⎕VFI ⎕UCS piducs
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
            :Trap 0 ⋄ 2 USend 'STOP' ⋄ :EndTrap

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
