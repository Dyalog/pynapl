# PyEvaluator
# -*- coding: utf-8 -*- 

# NOTE: this file should be compatible with both Python 2 and 3 with the
# minimal amount of future imports, since they will potentially mess with
# Python 2 code that's passed in.

from __future__ import absolute_import

from .Array import *

class PyEvaluator(object):
    """Evaluate a Python expression"""

    # If it's stupid and it works, it's still stupid, but at least it works
    wrapper=compile(u"retval = eval(code)",u'<APL>',u'exec')
 
    @staticmethod
    def executeInContext(script, apl):
        """Run Python code"""
        code = compile(script, '<APL>', 'exec')
        globals()["APL"]=apl
        exec(code,globals())

    def __init__(self, expr, args, conn):
        self.args=args
        self.pyargs=[]
        self.expr=expr
        self.conn=conn
        self.__expr_arg_subst()
        self.__check_arg_lens_match()

    def __expr_arg_subst(self):
        narg = 0
        build = []
        inString = False
        sDelim = u""
        escape = False

        i=0
        while i < len(self.expr):
           
            # if this character is escaped, skip it
            if escape:
                escape=False
                build.append(self.expr[i])
                i+=1
                continue

            
            # if \ in a string, the next character is excaped
            if inString and self.expr[i] == u'\\':
                escape=True
                build.append(self.expr[i])
                i+=1
                continue

            # if in a string, check if this is the delimiter
            if inString:
                if self.expr[i:i+len(sDelim)]==sDelim:
                    # this is the end of the string
                    inString=False
                    build.append(self.expr[i:i+len(sDelim)])
                    i+=len(sDelim)
                else:
                    # keep searching
                    build.append(self.expr[i])
                    i+=1
                continue

            # if not in a string, check if this is the start of a multiline string
            if self.expr[i:i+3] in (u"'''", u'"""'):
                # multiline string
                sDelim = self.expr[i:i+3]
                inString = True
                build.append(self.expr[i:i+3])
                i+=3
                continue

            # single-line string
            if self.expr[i] in u'\'"':
                sDelim = self.expr[i]
                inString = True
                build.append(self.expr[i])
                i+=1
                continue

            # if it's not any 
            ch=self.expr[i]
            if ch in u'⎕⍞':
                build.append(u'args[%d]' % narg)
                curarg = self.args[[narg]]
                if ch==u'⎕' and (isinstance(curarg,APLArray) 
                              or isinstance(curarg,APLNamespace)
                              or isinstance(curarg,APLObjectFactory)
                              or isinstance(curarg,ObjectRef)):
                    # this argument should be converted to a suitable Python representation
                    self.pyargs.append(curarg.to_python(self.conn.apl))
                else:
                    self.pyargs.append(curarg)
                    
                narg+=1
            else:
                build.append(ch)
            i+=1

        self.expr=compile(u''.join(build), u'<APL>', u'eval')

    def __check_arg_lens_match(self):
        if self.args.rho[0] != len(self.pyargs):
        #if self.args.rho[0] != sum(ch in u"⎕⍞" for ch in self.expr):
            raise TypeError("expression argument length mismatch")

            

    def go(self):
        local = {'args':self.pyargs, 'retval':None, 'code':self.expr, 'APL':self.conn.apl}
        exec(self.wrapper, globals(), local)
        retval = local['retval']
        #print("retval = %s: %s"%(repr(type(retval)), repr(retval)))

        if not isinstance(retval, APLArray):
            retval = APLArray.from_python(retval, True, self.conn.apl)
            #print("Converting to APLArray")
            #print("retval = %s: %s"%(repr(type(retval)), repr(retval)))
              
        return retval 

