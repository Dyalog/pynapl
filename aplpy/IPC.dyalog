:Namespace IPC
    ⍝ Send messages between the APL and Python process
    ⍝ w/o the overhead of Conga.

    ⍝ The IPC functions signal 999 on error,
    ⍝ and 998 on interrupt.

    ⍝ Use named pipes on Unix
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
                ⍝ We want to respond to APL interrupts and OS interrupts the same way.
                :Trap 1000
                    x←Read_ n 
                :Else
                    'Interrupt' ⎕SIGNAL 998
                :EndTrap
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
            ∇ x←Read_ n;r;bytes
                :Access Public
                r bytes←#.IPC.Unix.read id(n/0)n
                :If r=¯1
                    ⍝ Something went wrong
                    :If #.IPC.Unix.geterrno=#.IPC.Unix.EINTR
                        ⍝ We were interrupted, this is possible.
                        ⍝ No data was received.
                        'EINTR'⎕SIGNAL 998
                    :Else
                        'Cannot read'⎕SIGNAL 999
                    :EndIf
                :EndIf

                x←r↑bytes
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
