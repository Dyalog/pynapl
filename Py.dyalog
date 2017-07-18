:Namespace Py
    path←''
    
    ⍝ functions to interface with the operating system
    :Interface OSInterface
        
    :EndInterface
    
    
    :Class UnixInterface : OSInterface
        
        ∇ id←StartPython
          ⎕SH' python ',path
        ∇
    :EndClass
:EndNamespace
