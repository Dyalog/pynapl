:Namespace PyTest

    num←0
    ∇ r←Click;update
        num+←1
        ⎕←'Hello! ',num
        
        ⍝ 'py' is available here because this function is called from Python
        ⍝ this calls the "updateLabel" function defined below in Python
        update←(py.PyFn 'updateLabel').Call
        {}update num

        r←0 ⍝ callback expects a value back, any value
    ∇

    ∇ PyTest;py
        py←⎕NEW #.Py.Py
        py.Exec #.Py.ScriptFollows
        ⍝ import Tkinter
        ⍝
        ⍝ lbl=None
        ⍝
        ⍝ def start():
        ⍝  global lbl
        ⍝  window=Tkinter.Tk()
        ⍝  window.title="GUI Test"
        ⍝  window.geometry("300x300")
        ⍝  btn=Tkinter.Button(window, text="Hello APL",
        ⍝           command=APL.fn("#.PyTest.Click"))
        ⍝  btn.pack()
        ⍝  lbl=Tkinter.Label(window, text="---")
        ⍝  lbl.pack()
        ⍝  window.mainloop()
        ⍝  return 1
        ⍝
        ⍝ def updateLabel(newNum):
        ⍝  global lbl
        ⍝  lbl.config(text=str(newNum))
        
        'start()'py.Eval ⍬
    ∇


:EndNamespace
