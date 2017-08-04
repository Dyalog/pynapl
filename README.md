# APL-Python bridge

This is a bridge between Dyalog APL and Python. It allows Python
code to be accessed from APL, and vice versa.

## User manual

### Accessing Python from APL

The APL side of the bridge is located in `Py.dyalog`. 
It can be loaded into the workspace using:

```apl
]load Py
```

Note that it expects the included Python scripts to be
in the same directory as the `Py.dyalog` file.

#### Starting a Python interpreter

To start a Python interpreter, make a new instance of the
`Py.Py` class. This will start a Python instance in the background,
and connect to it. 

```apl
py ← ⎕NEW Py.Py
```

The resulting object can be used to interact with the Python
interpreter. Once the object is destroyed, the Python interpreter
associated with it will also be shut down.

There are several different options that can be given to the Py
class, namely:

| Option | Argument | Purpose |
| --- | --- | --- |
| `Attach` | ignored | Do not start up a Python instance, but allow attachment to one that is already running. A port number will be given, and it will wait for a connection from the Python side. The Python side can be told to connect using `APL.client(port)`. |
| `PyPath` | path to an interpreter | Start the Python interpreter given in the argument, instead of the system one. |
| `ArgFmt` | string, where `⍎` will be replaced by the path to the slave script, and `⍠` by the port number | When used in combination with `PyPath`, use a custom argument format rather than the standard one. |
| `Version` | major Python version (2 or 3) | Start either a Python 2 or 3 interpreter, depending on which is given. The default is currently 2. |
| `Debug` | boolean | If the boolean is 1, turns on debug messages and also does not start up a Python instance. |


In particular, the following might be of interest:

```apl
py ← ⎕NEW Py.Py('Version' 3) ⍝ use Python 3 instead of 2
```

```apl
⍝ start a Blender instance and control that instead of a normal Python
⍝ (if on Windows, you have to pass in the absolute path to blender.exe instead)
py ← ⎕NEW Py.Py (('PyPath' 'blender') ('ArgFmt' '-P "⍎" -- ⍠ thread'))
```



#### Running Python statements

The `Exec` function can be used to run one or more Python
statements. It takes one string, which may have newlines in it.
The `Py.ScriptFollows` function can be used to help load scripts.

```apl
⍝ run one statement
py.Exec 'import antigravity'

⍝ run a script
py.Exec 'def foobar():',(⎕UCS 10),'  return "abc"'

⍝ or (in a tradfn):
py.Exec #.Py.ScriptFollows
⍝ def foobar():
⍝    return "abc"
```

An `APL` object will be available to the Python code, in order
for it to call back into the APL code. (See the "Accessing APL code
from Python" section for more information.)

#### Evaluating Python expressions

The `Eval` function can be used to evaluate a Python expression.
It takes as its left argument the Python expression to be evaluated,
and as its right argument a vector of APL arguments to be substituted
into it. Inside the Python expression, the quad (`⎕`) or the quote-quad
(`⍞`) can be used to refer to these arguments. If the quad is used,
the argument will be converted to a (hopefully) suitable Python
representation first; if the quote-quad is used, the argument will be
exposed on the Python side as an `APLArray` object. (See the "Data
conversion" section for more information.)

If the Python expression returns something other than an `APLArray`,
it will be converted back into a suitable APL form before being sent back
to APL.

```apl
     ⍝ access a variable
     '__name___' py.Eval ⍬
APLPyConnect

     ⍝ add two numbers
     '⎕+⎕' py.Eval 2 2
4

     ⍝ this is equivalent to ⍴X
     '⍞.rho' py.Eval ⊂5 5⍴⎕A
5 5

     ⍝ round trip
     'APL.eval("2+2")' py.Eval ⍬
4

     ⍝ alternate syntax when there are no arguments
     py.Eval 'APL.eval("2+2")' 
4
```

Just as with `Exec`, an `APL` object will be made available to the
Python expression.

#### Making Python functions available to APL

It is also possible to 'import' a Python function to the APL workspace.
The `PyFn` function can be used to create APL functions that call
Python functions automatically.

The `PyFn` function returns a namespace containing two functions,
`Call` and `CallVec`. 

 * `CallVec` takes a vector of arguments as its
right argument, and passes those into the Python function. It takes an
optional boolean vector as its left argument, which describes
whether or not to convert the arguments.

 * `Call` is a "normal" APL function. If used monadically, it calls
the Python function with one argument (`f(⍵)`); if used dyadically
it calls the Python function with two arguments (`f(⍺,⍵)`). The
arguments are always converted.

The namespace also includes a reference to the Py object that created
it, so it will not be destroyed until such functions themselves are.

Example:

```apl

⍝ import a Python module
py.Exec 'import webbrowser'

⍝ define a function from it in APL
⍝ this one handily takes only one argument so can be used monadically
showPage←(py.PyFn 'webbrowser.open').Call

⍝ this will now show a web page
showPage 'http://www.dyalog.com'
```

#### Error handling

If the Python code raises an exception, the bridge will signal a
DOMAIN ERROR. `⎕DMX.Message` will contain the string representation
of the Python exception. 

### Accessing APL from Python

The `APL.py` module contains a function that will start an APL
interpreter. Just like the APL side, it expects the `Py.dyalog`
script to be in the same directory. 

#### Starting an APL interpreter

An APL object can be obtained using the `APL.APL` function. This
will start a Dyalog instance in the background and connect to it.

```python
from aplpy import APL
apl = APL.APL()
```

An optional `dyalog` argument may be given to the `APL` function,
to specify the path to the `dyalog` interpreter. If it is not given,
on Unix the `dyalog` interpreter on the path will be used,
on Windows the registry will be consulted. 
The Dyalog instance will be shut down once the `apl` object is
destroyed.

#### Fixing an APL script

The `fix` function takes a string, which will be 2⎕FIX'ed on the
APL side. This can be used to load large amounts of APL code into
the interpreter. 

```python
apl.fix("""
:Namespace Test
foo←42
:EndNamespace
""")
```

#### Evaluating APL code

The `eval` function takes a string, which will be evaluated
using `⍎` on the APL side. Any extra arguments passed into
`eval` will be put into a vector and exposed as `∆` on the
APL side, and a `py` object will be available for the APL code
to communicate back to the Python interpreter. (See "Accessing
Python from APL".)

This is a relatively low-level function, and it is probably better
to use `fn` and `op`. 

Conversion of data *to* APL types is done automatically. (Anything
that's not an `APLArray` is converted.) The result of the evaluation
is converted back to the Python format unless `raw` is set.

```
>>> apl.eval("2+2")
4
>>> apl.eval("⎕A")
u'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
>>> apl.eval("⎕A", raw=True)
<Array.APLArray object at 0x7fb704e36310>
>>> apl.eval("'2+2' py.Eval ⍬") # round trip
4
```

#### Making APL functions available to Python

The `fn` function can be used to import an APL function to Python.
The function may be niladic (if called with no arguments),
monadic (if called with one argument), or dyadic (if called with
two).

As with `eval`, a named argument `raw` can be set to prevent
automatic data conversion.

```
>>> aplsum = apl.fn("+/")
>>> aplsum([1,2,3,4,5])
15
>>> aplsum(3, [1,2,3,4,5])
[6, 9, 12]
```

The function may be an anonymous dfn and may contain newlines.
It may *not* be a definition of a tradfn (those can be defined
using `fix` or `tradfn`, then referred to by name using `fn`).

```python
>>> factorial = apl.fn("""
{ ⍵≤0:1
  ⍵×∇⍵-1
}
""")
>>> factorial(5)
120
```

##### Defining a tradfn using Python

Apart from using `fix`, a tradfn can also be defined using the
`tradfn` function:

```python
>>> foo = apl.tradfn("""
r←foo x
r←x+x
""")
>>> foo(5)
10
>>> apl.fn("foo")(5)
10
```

#### Making APL operators available to Python

Python does not make the difference between functions and
operators that APL makes. Therefore, APL operators can be
exposed as Python functions using the `op` function.

```
>>> scan = apl.op("\\") # note the extra backslash for escaping
```

The operator is then exposed as a Python function, which takes 
one or two arguments, depending on whether the operator is 
monadic or dyadic.

The arguments may be either values or Python functions.
If you want to pass an APL function to an APL operator via Python,
you must first import the APL function using `fn`. 

```
>>> apl_add = apl.fn("+")
>>> py_add = lambda x, y: x+y
>>> apl_sumscan = scan(apl_add) # equivalent to "+\"
>>> py_sumscan = scan(py_add)   # uses the Python "+"
>>> apl_sumscan([1,2,3])
[1, 3, 6]
>>> py_sumscan([1,2,3])
[1, 3, 6]
```

If an APL operator is applied to an APL function via Python,
as in the `apl_sumscan` example, this is detected, and the application
is done in APL without calling back into Python. 

#### Error handling

If a signal is raised by the APL code, an APLError will be raised
on the Python side. The exception object will contain a `dmx` field,
which is a dictionary that contains the fields from `⎕DMX`. 

When an interrupt is raised, the message will be `"Interrupt"` and
`dmx` will be `None`. 

### Data conversion

#### From Python to APL

 * Numbers (any kind) or boolean: number
 * One-character strings: characters
 * Other string: character vector
 * List or tuple: vector
 * NoneType: empty numeric vector
 * Dictionary: namespace

In addition, any kind of iterable object (objects that are instances
of `collections.Iterable` or that implement `__iter__`, and objects
that implement both `__len__` and `__getitem__`) will be iterated over,
and the results sent as a vector to APL. This allows for most kinds of
custom container objects to be used. 

_NOTE_: if the object is an infinite generator, it will cause a hang.


#### From APL to Python

 * Numbers: int, long, or float, depending on which fits best
 * Simple (non-nested) character vector: Unicode string
 * Numeric vector / nested vector: List
 * Higher-rank array: nested list (the equivalent of
   `{↓⍣((⊃⍴⍴⍵)-1)⊢⍵}` is done).
 * Namespace containing values: dictionary

#### The `APLArray` class

This is a class on the Python side that can be used to communicate
with APL without going through the conversion. It is a multidimensional
array, which may contain nested APLArray objects.

An APLArray object can be indexed using a list or a tuple.
The index should be given as if `⎕IO=0`, e.g.:

```
>>> foo = apl.eval("5 5⍴⎕A", raw=True)
>>> foo.rho
[5, 5]
>>> foo[2,3]  # ⎕IO←0 ⋄ (5 5⍴⎕A)[2;3]
u'N'
```

Assignment to individual items is possible in the same manner.
Conversion will be done automatically if it is necessary.
An `IndexError` will be raised if the coordinates are out of
range.

## Implementation details

Whichever side initiates will find an unused port, and start up a
network server. It will listen for a connection from `localhost`.
It will then start up the other side, and run a client program
which will be used to run code there. 

### Communication

The both programs communicate by sending each other messages,
as described below.

#### Message Format

The underlying format used for messages consists of a 5-byte header
and then a body.

The first byte of the header denotes the message type, the next four
give the length of the body in bytes (high-endian). 

The contents of the body are UTF-8 encoded text, usually JSON.

#### Message Types

| Message Type | Contents | Purpose |
| --- | --- | --- |
| `0` (`OK`) | ignored | returned to signal nothing has gone wrong |
| `1` (`PID`) | the PID of the process, as UTF-8 text | sent by the client on startup |
| `2` (`STOP`) | ignored | tells the client to shut down |
| `3` (`REPR`) | an UTF8-encoded string of code | runs the code on the other side and sends `REPRRET` back with the string representation of the result (for debugging) |
| `4` (`EXEC`) | an UTF8-encoded string of code, which does not return a value | runs the code on the other side, and sends back `ERR` or `OK`. For APL this `⎕FIX`es the code |
| `5` (`REPRRET`) | an UTF8-encoded string | sends back the result of an earlier `REPR` |
| `10` (`EVAL`) | a JSON array of two elements, the first being a string of code and the second being an array of serialized objects | evaluates the expression given the arguments, and sends back the result using `EVALRET` |
| `11` (`EVALRET`) | a serialized object | the result of an earlier `EVAL` |
| `253` (`DBGSerializationRoundTrip`) | a serialized object | deserializes and reserializes the object on the other side, then sends the result back using the same message code (for debugging) |
| `255` (`ERR`) | an UTF-8 string containing the description of the error | signal an error |

#### Reentrancy

The message handling code on both sides supports handling messages while
waiting for the result of another. E.g., if an `EVAL` is sent, it may
cause another `EVAL` to be sent back, which will then be handled before
the corresponding `EVALRET` is received. This way, the evaluation of an
expression may switch back and forth between the two sides as needed.

Example:

```
Python side:
>>> x = apl.eval("2+'2+2' py.Eval ⍬")
 # Python sends to APL: EVAL '2+2' py.Eval ⍬
 
APL side:
     2+'2+2' py.Eval ⍬
 ⍝ APL sends back to Python: EVAL 2+2

Python side:
>>> 2+2
 # this evaluates to 4
 # Python sends to APL: EVALRET 4
http://localhost:8888/notebooks/Untitled4.ipynb?kernel_name=apl
APL side:
 ⍝ receives EVALRET 4
     2 + 4
 ⍝ this evaluates to 6
 ⍝ APL sends to Python: EVALRET 6

Python side:
 # receives EVALRET 6
 # the final answer is 6 
>>> x
6
```
