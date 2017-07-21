:Namespace PyTest
       
    
    N←⎕UCS 10 13
   
    pycode← 'import Tkinter',N
    pycode,←'def start(APL):',N
    pycode,←' window=Tkinter.Tk()',N
    pycode,←' window.title="GUI Test"',N
    pycode,←' window.geometry("300x300")',N
    pycode,←' btn=Tkinter.Button(window, text="Hello APL",',N
    pycode,←'         command=lambda:APL.eval("#.PyTest.Click⋄1"))',N
    pycode,←' btn.pack()',N 
    pycode,←' APL.lbl=Tkinter.Label(window, text="---")',N
    pycode,←' APL.lbl.pack()',N
    pycode,←' window.mainloop()',N
    pycode,←' return 1'
    
    
    num←0
    ∇ Click
      num+←1
      ⎕←'Hello! ',num
      ⍝⎕←'P:', 'APL.eval("#.PyTest.num")' py.Eval⍬
      py.Exec 'APL.lbl.config(text=str(APL.eval("#.PyTest.num")))'
    ∇
    
    ∇ PyTest;py
      py←⎕NEW #.Py.Py
      py.Exec pycode
      'start(APL)'py.Eval ⍬
    ∇
    

:EndNamespace
