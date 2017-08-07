:Namespace PyTest

    num←0
    ∇ r←ClickHello;update
        num+←1
        ⎕←'Hello! ',num

        ⍝ 'py' is available here because this function is called from Python
        ⍝ this calls the "updateLabel" function defined below in Python
        update←(py.PyFn 'updateLabel').Call
        {}update num

        r←0 ⍝ callback expects a value back, any value
    ∇

    ∇ r←ClickRun;apl
        ⎕←'⍎ clicked'
        
        ⍝ get code from Python
        apl←py.Eval 'aplbox.get("1.0",Tkinter.END)'
        ⎕←'Running: ',apl
        
        r←⍬
        :Trap 0
            r←(¯2↑1,⍴r)⍴r←⍕1(85⌶)apl~⎕TC
            'messagebox.showinfo(⎕,"\n".join(⎕))' py.Eval '⍎' r
        :Case 85
            'messagebox.showinfo(⎕,⎕)' py.Eval '⍎' 'OK'
        :Else
            'messagebox.showerror(⎕,⎕)' py.Eval '⍎' (⎕DMX.Message)
        :EndTrap
        r←0
    ∇
    
    ∇ PyTest;py
        py←⎕NEW #.Py.Py ('Version' 3)
        py.Exec #.Py.ScriptFollows
        ⍝ import tkinter as Tkinter
        ⍝ from tkinter import messagebox
        ⍝
        ⍝ lbl=None
        ⍝ aplbox=None
        ⍝
        ⍝ def start():
        ⍝  global lbl, aplbox
        ⍝  
        ⍝  window=Tkinter.Tk()
        ⍝  window.title("GUI Test")
        ⍝  btn=Tkinter.Button(window, text="Hello APL",
        ⍝           command=APL.fn("#.PyTest.ClickHello"))
        ⍝  btn.pack()
        ⍝  lbl=Tkinter.Label(window, text="---")
        ⍝  lbl.pack()
        ⍝
        ⍝  aplbox=Tkinter.Text(window)
        ⍝  aplbox.pack()
        ⍝
        ⍝  btn2=Tkinter.Button(window, text="⍎",
        ⍝           font=('Helvetica',16),
        ⍝           command=APL.fn("#.PyTest.ClickRun"))
        ⍝  btn2.pack()
        ⍝  
        ⍝  window.mainloop()
        ⍝  return 1
        ⍝
        ⍝ def updateLabel(newNum):
        ⍝  global lbl
        ⍝  lbl.config(text=str(newNum))

        'start()'py.Eval ⍬
    ∇


:EndNamespace
