⍝ The Python code will write the 'WinDyalogPort.dyalog' file that defines
⍝ the port this should listen on.
⍝ If it's stupid but it works, it's still stupid, but at least it works.

:Namespace WinPySlave

    ⎕IO ⎕ML←1
    
    ∇ Go
        :If 0=⎕NC'#.Py'
            ⎕←'ERROR: Py did not load.'
        :ElseIf 0=⎕NC'#.WinPort'
            ⎕←'ERROR: WinPort did not load.'
        :Else 
            ⍝ only TCP for now
            #.Py.StartAPLSlave 'TCP' #.WinPort.port
            ⎕OFF
        :EndIf
    ∇
    
:EndNamespace