:Namespace Py
    ⎕IO ⎕ML←1
    when←/⍨

    filename←'APLBridgeSlave.py'
    attempts←10

    host←'localhost'
    ⍝port←2526

    ready←0
    threadno←⍬
    
    serverSocket←'SPy'
    connSocket←'SPy'


    :Class UnixInterface
        ⍝ Functions to interface with Unix OSes

        ∇ r←GetPath fname
            :Access Public
            r←(⌽∨\⌽'/'=fname)/fname
        ∇

        ∇ StartPython program;cmd
            :Access Public
            cmd←'python ',program
            ⎕SH cmd
        ∇
    :EndClass


    ⍝ Find an open port and start a server on it
    ∇ port←StartServer;tryPort;rv
        :For tryPort :In ⌽⍳65535
            rv←⊃#.DRC.Srv serverSocket 'localhost' tryPort 'Raw'
            :If rv=0
                port←tryPort
                ⎕←'Started server on port ',port
                :Return
            :EndIf
        :EndFor
        port←¯1
    ∇
    
    ⍝ Wait for connection, set connSocket if connected
    ∇ success←AcceptConnection;rc;rval
        success←0
        :Repeat
            rc←⊃rval←#.DRC.Wait serverSocket
            :If rc=0
                ⎕←'Connection established'
                connSocket←2⊃rval
                ⎕←'Socket: ',connSocket
                success←1
                :Leave
            :ElseIf rc=100
                ⍝ Timeout
                ⎕←'Timeout, retrying'
            :Else
                ⍝ Error
                ⎕←'Socket error ' rval
                success←0
                :Leave
            :EndIf            
        :EndRepeat
    ∇

    ⍝ Send Unicode message
    ∇ success←mtype USend data
        success←mtype Send 'UTF-8' ⎕UCS data
    ∇



    ⍝ Send message (as raw data)
    ∇ success←mtype Send data;send;sizefield

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
        success←0=⊃⎕←#.DRC.Send connSocket (⎕←mtype,sizefield,data)
    ∇

    ⍝ debug function (eval/repr)
    ∇ str←Eval code;succ;mtype;recv
        ⍝ send the message
        :If ~3 USend code
            ⎕←'Send failure'
            →0
        :EndIf

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


    ⍝ Receive Unicode message
    ∇ (success mtype recv)←URecv;s;m;r
        s m r←Recv
        (success mtype recv)←s m ('UTF-8' (⎕UCS⍣s) r)
    ∇

    ⍝ Receive message.
    ⍝ Message fmt: X L L L L Data
    reading←0 ⋄ curlen←¯1 ⋄ type←¯1 ⋄ data←''
    ∇ (success mtype recv)←Recv;done;wait_ret;rc;obj;event;sdata;tmp
        :If ~ready
            success mtype recv←0 ¯1 'Not initialized.'
            ready←0
            →finish
        :EndIf

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

    ⍝ Initialization routine
    ∇ Init;ok;tries;code;clt;success;_;msg;srvport;piducs
        reading←0 ⋄ curlen←¯1 ⋄ data←'' ⋄ type←¯1

        ⍝ load Conga
        :If 0=⎕NC'#.DRC'
            'DRC'#.⎕CY 'conga.dws'
        :EndIf

        #.DRC.Init ''

        ⍝ Attempt to start a server
        ⎕←'Starting server'
        srvport←StartServer
        ⎕←'Server at ' srvport

        ⍝ find path
        os←⎕NEW UnixInterface
        pypath←(os.GetPath SALT_Data.SourceFile),filename

        ⍝ start python
        ⍝{os.StartPython&⍵} pypath
        ⎕SH 'python ',pypath,' ',(⍕srvport),'>/home/marinus/log &'

        ready←1

        ⍝ Python client should now send PID
        ⎕←'Waiting for connection... '
        
        :If ~AcceptConnection
            ⎕←'Failure.'
            →ready←0
        :EndIf
        
        success msg piducs←⎕←Recv

        :If ~success
            ⎕←'Failure.'
            →ready←0
        :EndIf

        pid←⎕VFI ⎕UCS piducs
        :If ~success
            ⎕←'PID not a number'
            →ready←0
        :EndIf

        ⎕←'OK! pid='pid     

    ∇


:EndNamespace
