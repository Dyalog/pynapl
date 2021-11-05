# Mandelbrot set image generator

This demo uses part of the APL code from the [“Drawing the Mandelbrot Set”][mandelbrot-webinar] webinar
to generate a 3D array representing the Mandelbrot set,
and then using Python (`numpy` and `PIL`) to draw the image to an image file.

[mandelbrot-webinar]: https://www.youtube.com/watch?v=ozaRMHeYWYM


## Run this demo

This demo has external Python dependencies, so start by installing those with

```bash
python -m pip install -r requirements.txt
```

To run this demo, you will need the `Grid`, `Mandelbrot`, `Palette`, and `CreateImage` functions in your namespace.
(For example, link them under the namespace `mand`).

To create a Mandelbrot set image,

 1. create a grid representing the area you care about:

```APL
grid ← ¯.7 (3 2) mand.Grid 300
```

 2. define the maximum number of iterations the algorithm will run for, and apply it:

```APL
maxiter ← 40    ⍝ To go well with `Palette`, must be a multiple of 4.
fract ← maxiter mand.Mandelbrot grid
```

 3. create a colour palette and use it to convert the fractal grid:

```APL
palette ← mand.Palette maxiter
img ← palette[;fract]       ⍝ 3D array where the major cells are the RGB colour channels.
```

 4. create the pynapl connection:

```APL
]load path/to/pynapl/Py
]cd path/to/pynapl
py ← ⎕NEW Py.Py
```

 5. save the image to disk:

```APL
_ ← py mand.CreateImage img 'path/to/save/image/to/fractal.png'
```
