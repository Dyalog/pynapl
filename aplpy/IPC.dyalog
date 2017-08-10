:Namespace IPC
    ⍝ Send messages between the APL and Python process
    ⍝ w/o the overhead of Conga.

    ⍝ The IPC functions signal 999 on error,
    ⍝ and 998 on interrupt.



    ∇Init
        ⍝ Figure out which OS we're on and select the correct IPC class
        :If 'Windows'≡7↑⊃#.⎕WG'APLVersion'
            ⍝ In a world without walls, who needs Windows and Gates?
            #.IPC.Windows.Init
            #.IPC.OS←#.IPC.Windows
        :ElseIf 'Linux'≡5↑⊃#.⎕WG'APLVersion'  
            ⍝ WE HAVE A GREAT OPERATING SYSTEM, FOLKS, THE BEST
            #.IPC.Unix.Init
            #.IPC.OS←#.IPC.Unix
        :EndIf             
    ∇


    ⍝ Use Conga
    :Namespace TCP
        ∇ Init  
            ⍝ load Conga
            :If 0=⎕NC'#.DRC'
                'DRC'#.⎕CY'conga.dws'
            :EndIf

            :If 0≠⊃#.DRC.Init ''
                'Conga is unavailable.' ⎕SIGNAL 999
            :EndIf

        ∇       

        :Class Connection
            :Field reading←0
            :Field curlen←¯1
            :Field curdata←''
            :Field curtype←¯1

            :Field socket←⍬
            :Field srvsock←⍬

            :Field ready←0

            ∇n←Name
                :Access Public
                n←'TCP/IP'
            ∇

            ∇Connect (host port);rv
                :Access Public
                rv←#.DRC.Clt '' host port 'Raw'
                :If 0=⊃rv
                    ⍝ connection established
                    socket←2⊃rv
                    ready←1
                :Else
                    ⍝ failure
                    'Failed to connect' ⎕SIGNAL 999
                :EndIf
            ∇

            ⍝Start a server
            ∇port←StartServer;tryPort;rv
                :Access Public
                :For tryPort :In ⌽⍳65535
                    rv←#.DRC.Srv '' 'localhost' tryPort 'Raw'
                    :If 0=⊃rv
                        port←tryPort
                        srvsock←2⊃rv
                        :Return
                    :EndIf
                :EndFor

                'Failed to start server' ⎕SIGNAL 999
            ∇

            ⍝ Wait for a connection
            ∇AcceptConnection;rc;rval
                :Access Public
                :Repeat
                    rc←⊃rval←#.DRC.Wait srvsock
                    :If rc=0
                        socket←2⊃rval
                        ready←1
                        :Leave
                    :ElseIf rc=100
                        ⍝ timeout
                        ⍞←'.'
                        ⎕DL÷4
                    :Else
                        ('Failed to accept connection ',⍕rval)⎕SIGNAL 999
                    :EndIF 
                :EndRepeat
            ∇

            ∇Write data;rc
                :Access Public

                'Inactive connection'⎕SIGNAL(~ready)/999

                rc←#.DRC.Send socket data
                :If 0≠⊃rc    
                    ready←0
                    ('Socket error ',⍕rc)⎕SIGNAL 999
                :EndIf
            ∇     

            ∇Close
                :Access Public

                {}#.DRC.Close socket
                :If srvsock≢⍬
                    {}#.DRC.Close srvsock   
                :EndIf 
                ready←0
            ∇

            ∇data←Read nbytes;interrupt;tS;rc;wait_ret;obj;event;sdata;r
                :Access Public          

                'Inactive connection'⎕SIGNAL(~ready)/999 

                interrupt←0 

                :Trap 1000
                    :Repeat   
                        :If nbytes≤≢curdata
                            ⍝ signal interrupt if necessary
                            :If interrupt
                                interrupt←0
                                'Interrupt'⎕SIGNAL 998
                            :EndIf

                            ⍝ there is enough data to return
                            data←nbytes↑curdata
                            curdata↓⍨←nbytes

                            →out
                        :Else
                            ⍝ there is not, so go read some more

                            :Repeat
                                :If interrupt
                                    interrupt←0
                                    'Interrupt'⎕SIGNAL 998 ⍝ to match the Unix pipes
                                :EndIf

                                tS←2503⌶1 ⍝ don't break while in Conga
                                rc←⊃wait_ret←#.DRC.Wait socket
                                {}2503⌶tS

                                :If rc=0
                                    ⍝ success
                                    rc obj event sdata←wait_ret
                                    :Select event
                                    :Case 'Block' ⍝ new data
                                        curdata ,← sdata
                                        :Leave
                                    :CaseList 'BlockLast' 'Error' ⍝ error
                                        →err
                                    :EndSelect
                                :ElseIf rc=100
                                    ⍝ timeout
                                    {}⎕DL ÷4 ⍝ wait 1/4th of a second and try again
                                :Else
                                    ⍝ neither success nor timeout: error
                                    →err
                                :EndIf
                            :EndRepeat
                        :EndIf
                    :EndRepeat  
                :Else
                    ⍝ interrupt, keep track that it happened and continue execution
                    interrupt←1
                    →⍎1↓(+\+⌿1 ¯1×[1]'[]'∘.=r)/r←(∧\' '≠r)/r←2⊃⎕DM
                :EndTrap  
                →out

                err:
                ready←0
                ('Socket error ',⍕wait_ret)⎕SIGNAL 999 
                out:
            ∇
        :EndClass
    :EndNamespace

    :Namespace Windows   
        :Section Assorted Windows constants
            GENERIC_WRITE←16⊥4 0 0 0 0 0 0 0
            GENERIC_READ ←16⊥8 0 0 0 0 0 0 0
            CREATE_NEW   ←1
            FILE_ATTRIBUTE_NORMAL←128  
            PIPE_ACCESS_DUPLEX←3
            PIPE_ACCESS_INBOUND←1
            PIPE_ACCESS_OUTBOUND←2 
            PIPE_TYPE_BYTE←0

        :EndSection
        ∇ Init  
            ⎕NA'P  Kernel32.dll|CreateNamedPipeW <0T[] U4 U4 U4 U4 U4 U4 P'
            ⎕NA'P  Kernel32.dll|CreateFileW <0T[] U4 U4 P U4 U4 P'
            ⎕NA'I  Kernel32.dll|WriteFile& P <U1[] U4 >U4'
            ⎕NA'I  Kernel32.dll|ReadFile& P =U1[] U4 >U4'
            ⎕NA'I  Kernel32.dll|CloseHandle P'
            ⎕NA'U4 Kernel32.dll|GetLastError' 
            ⎕NA'I  Kernel32.dll|PeekNamedPipe P =U1[] U4 >U4 >U4 >U4'  
            ⎕NA'I  Kernel32.dll|ConnectNamedPipe& P P'
            ⎕NA'   Rpcrt4.dll  |UuidCreate >U1[8]'
        ∇

        :Class FIFO
            :Field Private name
            :Field Private handle
            :Field Private open←0 
            :Field Private mkNew←0

            :Field Private pipeReadWaiting←0
            :Field Private NAME_PFX←'\\.\pipe\APLPY-'

            ⍝ See what the invalid handle is   
            ∇i←invalidHandle                
                :Access Public

                ⍝ This is a very hacky way to do it, but it "works". 
                ⍝ The name is known invalid and so is the max_instances parameter (256).
                i←#.IPC.Windows.CreateNamedPipeW ',\!INVALID!\,' 2 0 256 512 512 0 0
            ∇                                                                       

            ∇initNew;r  

                :Access Public
                :Implements Constructor

                mkNew←1                              

                ⍝ generate a random name for our pipe
                ⎕←'Initializing pipe ',name←NAME_PFX,1↓∊'-',¨⍕¨#.IPC.Windows.UuidCreate 0  
            ∇    

            ∇initOpen fn
                :Access Public
                :Implements Constructor

                mkNew←0
                name←fn
            ∇             

            ∇ destroy
                :Implements Destructor
                Close
            ∇

            ⍝ See how much data is available
            ∇ (b data avl)←Peek_ n;dummy1;rd;dummy2
                :Access Public
                b data rd avl dummy2←#.IPC.Windows.PeekNamedPipe handle (n/0) n 0 0 0
            ∇  

            ∇ n←Name
                :Access Public
                n←name
            ∇


            readbuf←⍬
            ∇ data←Read nbytes;b;avl;err;data 
                :Access Public
                ⍝ This probably isn't the best way to do APL-interruptable synchronous I/O

                ⍝ Busy-wait until we have enough data available
                :Trap 1000  
                    retry:   →skip
                    readbuf←⍬  
                    :Repeat 
                        b data avl←Peek_ nbytes
                        pipeReadWaiting×←~b
                    :Until (~b)∨avl≥nbytes

                    ⍝ If we can't peek, then something has gone horribly wrong   
                    :If ~b
                        err←#.IPC.Windows.GetLastError
                        :If err=230
                        :AndIf pipeReadWaiting
                            ⍝ we're just still waiting for the connection
                            ⎕DL ÷2                                      
                            →retry
                        :Else
                            ('Something has gone wrong: ',⍕err) ⎕SIGNAL 999
                        :EndIf
                    :EndIf                                               

                    skip:
                    ⍝ We should now have enough data available to read, so read it 
                    pipeReadWaiting←0
                    data←Read_ nbytes
                :Else                      
                    ⍝ This is to match the Unix interface, which signals EINTR
                    ⍝ if it is interrupted. Windows doesn't quite do interrupts.
                    'Interrupt' ⎕SIGNAL 998
                :EndTrap
            ∇

            ⍝ Low-level read
            ∇ data←Read_ nbytes;r;n;bytes
                :Access Public
                r bytes n←#.IPC.Windows.ReadFile handle (nbytes/0) nbytes 0 
                :If r=0
                    ('Windows error: ',⍕#.IPC.Windows.GetLastError)⎕SIGNAL 999
                :EndIf
                data←n↑bytes
            ∇   

            ⍝ Dunno if we need any special wrapping for this but we'll see
            ∇ Write bytes;r 
                :Access Public
                {}Write_ bytes
            ∇

            ∇ n←Write_ bytes;r
                :Access Public
                r n←#.IPC.Windows.WriteFile handle bytes (≢bytes) 0
                :If r=0
                    ('Windows error: ',⍕#.IPC.Windows.GetLastError)⎕SIGNAL 999
                :EndIf
            ∇

            ⍝ Close the handle
            ∇ Close
                :Access Public
                →(~open)/0
                open←0
                {}#.IPC.Windows.CloseHandle handle
            ∇                                              

            ⍝ New pipe
            ∇ New_ mode
                :Access Public                
                handle←#.IPC.Windows.CreateNamedPipeW name mode 0 255 1024 1024 0 0 
                'Cannot create pipe'⎕SIGNAL(handle=invalidHandle)/999
                #.IPC.Windows.ConnectNamedPipe handle 0
                open←1
            ∇ 

            ⍝ Open pipe
            ∇ Open_ mode;err
                :Access Public
                handle←#.IPC.Windows.CreateFileW name mode 3 0 3 #.IPC.Windows.FILE_ATTRIBUTE_NORMAL 0 
                err←#.IPC.Windows.GetLastError
                ('Cannot open pipe: ',⍕err)⎕SIGNAL(handle=invalidHandle)/999 
                open←1
            ∇


            ⍝ Open for reading
            ∇ OpenRead
                :Access Public    
                pipeReadWaiting←1 ⍝ so we can disregard ERROR_BAD_PIPE until the other side connects
                :If mkNew
                    New_ #.IPC.Windows.PIPE_ACCESS_INBOUND
                :Else
                    Open_ #.IPC.Windows.GENERIC_READ
                :EndIf 

            ∇                               

            ⍝ Open for writing
            ∇ OpenWrite
                :Access Public
                :If mkNew
                    New_ #.IPC.Windows.PIPE_ACCESS_OUTBOUND  
                :Else
                    Open_ #.IPC.Windows.GENERIC_WRITE
                :EndIf
            ∇


        :EndClass       
    :EndNamespace

    :Namespace Unix

        :Section Assorted Linux constants
            POLLIN←1 ⍝ on Linux, at least
            O_RDONLY←0
            O_WRONLY←1
            O_RDWR←2 

            EINTR←4
        :EndSection

        ⍝ Load all the libraries
        ∇ Init
            'NonWindows'#.⎕CY'quadna.dws'
            #.NonWindows.Setup
            libc←#.NonWindows.libc ⍬
            ⎕NA'  ',libc,'|tmpnam =0C'
            ⎕NA'I ',libc,'|mkfifo <0C U4'
            ⎕NA'I ',libc,'|open <0C U'
            ⎕NA'I ',libc,'|close I'
            ⎕NA'I ',libc,'|unlink <0C'
            ⎕NA'I ',libc,'|write I <U1[] P'
            ⎕NA'I ',libc,'|read I =U1[] P'
            ⎕NA'I ',libc,'|poll ={I I2 I2}[] U8 I'

            ⎕NA'I ',#.NonWindows.dyalib,'geterrno'

        ∇


        ⍝ This class holds low-level file descriptor
        ⍝ for a named pipe
        :Class FIFO
            :Field Private name
            :Field Private id
            :Field Private interrupt←0

            :Field Private buf←⍬
            :Field Private open←0

            ⍝ Open one that has been given
            ∇ initName file;r
                :Access Public
                :Implements Constructor

                name←file

            ∇

            ⍝ Create one and open it
            ∇ initNew;r
                :Access Public
                :Implements Constructor

                ⍝ Make a new named pipe under a temporary name
                name←#.IPC.Unix.tmpnam⊂256↑''
                r←#.IPC.Unix.mkfifo name(8⊥6 0 0)
                'Cannot make pipe'⎕SIGNAL(r=¯1)/999
            ∇            

            ∇ destroy
                :Implements Destructor
                Close
            ∇

            ⍝ Get the file name
            ∇ n←Name
                :Access Public
                n←name
            ∇

            ⍝ Close the file
            ∇ Close
                :Access Public
                →(~open)/0
                {}#.IPC.Unix.close id
            ∇

            ⍝ Open the file
            ∇ Open_ mode
                :Access Public
                r←#.IPC.Unix.open name mode

                'Cannot open pipe'⎕SIGNAL(r=¯1)/999
                id←r
                open←1
            ∇

            ∇ OpenRead
                :Access Public
                Open_ #.IPC.Unix.O_RDONLY
            ∇

            ∇ OpenWrite
                :Access Public
                Open_ #.IPC.Unix.O_WRONLY
            ∇

            ⍝ Read an amount of bytes from the file.
            ∇ x←Read n;r;bytes;tS;dat
                :Access Public
                x←Read_ n        
            ∇

            ⍝ Write an amount of bytes to the file
            ∇ Write bytes;tS
                :Access Public
                ⍝ just disable interrupts during writing
                tS←2503⌶1
                {}Write_ bytes
                {}2503⌶tS
            ∇


            ⍝ Read an amount of bytes from the file
            ⍝ (Low-level)
            ∇ x←Read_ n;r;bytes;tS
                :Access Public
                retry:
                r bytes←#.IPC.Unix.read id(n/0)n
                tS←2503⌶1
                :If r=¯1
                    ⍝ Something went wrong
                    :If #.IPC.Unix.geterrno=#.IPC.Unix.EINTR
                        ⍝ retry
                        → retry  
                    :Else
                        'Cannot read'⎕SIGNAL 999
                    :EndIf
                :EndIf

                x←r↑bytes
                {}2503⌶tS
            ∇

            ⍝ Write an amount of bytes to the file
            ∇ x←Write_ bytes
                :Access Public
                x←#.IPC.Unix.write id bytes(≢bytes)
                'Cannot write'⎕SIGNAL(x=¯1)/999
            ∇


        :EndClass

    :EndNamespace

:EndNamespace
