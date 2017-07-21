:Namespace PyTest

    N←⎕UCS 10 13
   
    pycode← 'import Tkinter',N
    pycode,←'def start(APL):',N
    pycode,←' window=Tkinter.Tk()',N
    pycode,←' window.title="GUI Test"',N
    pycode,←' window.geometry("300x300")',N
    pycode,←' btn=Tkinter.Button(window, text="Hello APL",',N
    pycode,←'         command=lambda:APL.eval("#.PyTest.SayHi⋄1"))',N
    pycode,←' btn.pack()',N
    pycode,←' window.mainloop()',N
    pycode,←' return 1'
    
    ∇ SayHi
      ⎕←'Hello!'
    ∇
    
    ∇ PyTest;py
      py←⎕NEW #.Py.Py
      py.Exec pycode
      'start(APL)'py.Eval ⍬
    ∇
    

:EndNamespace
