# Game of Life simulation

This demo simulates Conway's Game of Life in a program window.
The program window is created and updated by `pygame`, a Python gaming library.

An interesting thing about this demo is that,
while Python is in charge of driving the program, handling user events,
and other similar things,
all the data simulation data is kept on the APL side and APL is responsible
for updating the simulation state.


## Run this demo

This demo depends on `pygame`, which is an external Python module.
Therefore, start by installing it with

```bash
python -m pip install -r requirements.txt
```

After that is done, just run the GUI with

```bash
python gol.py
```

The simulation is paused initially, and no cells are alive.

The <kbd>Spacebar</kbd> toggles the simulation pause state,
and <kbd>R</kbd> initialises the state randomly.

When the simulation is paused, the left mouse button can be used
to click (or click & drag) to set some cells to the alive state.

Pressing <kbd>E</kbd> will empty the screen/kill all cells.
