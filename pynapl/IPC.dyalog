:Namespace IPC
    ⍝ Send messages between the APL and Python process
    ⍝ w/o the overhead of Conga.

    ⍝ The IPC functions signal 999 on error,
    ⍝ and 998 on interrupt.



    ∇Init;isOS
        
        isOS←{⍵≡(≢⍵)↑⊃#.⎕WG'APLVersion'}
        
        ⍝ Figure out which OS we're on and select the correct IPC class
        :If isOS 'Windows'
            ⍝ NOTE: named pipes on Windows didn't work well, so for now TCP is used on Windows.
            ⍝ #.IPC.Windows.Init
            #.IPC.OS←#.IPC.Windows ⍝ this will NONCE ERROR if the rest of the code actually triees to use it
        :ElseIf isOS 'Linux'
        :OrIf isOS 'Mac'
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
        ∇ Init  
           ⍝ Windows removed, wasn't working well. For now, a TCP connection is used on Windows. 
        ∇

        :Class FIFO
            ∇initNew;r  
                :Access Public
                :Implements Constructor
                'Use TCP sockets on Windows.' ⎕SIGNAL 16
            ∇    
            ∇initOpen fn
                :Access Public
                :Implements Constructor
                'Use TCP sockets on Windows.' ⎕SIGNAL 16                                        
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
            ⍝ quadna.dws doesn't know where the mac C library is...
            :If 'Mac'≡3↑⊃#.⎕WG'APLVersion'
                libc←'/usr/lib/system/libsystem_c.dylib'
            :Else
                libc←#.NonWindows.libc ⍬
            :EndIf
            
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
