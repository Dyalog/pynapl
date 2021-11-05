"""
Game of Life simulation with editing capabilities.

Use the SPACEBAR to pause/resume the game evolution simulation.
When the simulation is paused, use the left mouse button to bring cells to life.
Pressing R should fill the board randomly.
Pressing E should empty the board.
"""

import enum
import sys
from typing import List, Tuple

import pygame

from pynapl import APL

Coordinates = List[Tuple[int, int]]

WIDTH = 1080
HEIGHT = 720
CELL_SIZE = 20
FPS = 60
GENS_PER_SEC = 3
_APL = APL.APL()


class Palette(enum.Enum):
    """Enum with the colours used."""
    BACKGROUND_COLOUR = (68, 71, 90)
    FOREGROUND_COLOUR = (248, 248, 242)


def set_status(positions: Coordinates, alive: bool):
    """Set the cells in the given positions to the given status."""
    _APL.eval(f"board ← {int(alive)}@∆⊢board", *positions)


def paint(
    screen: pygame.Surface,
    positions: Coordinates,
    alive: bool
) -> List[pygame.rect.Rect]:
    """Draw the given cells to be of the given status."""
    rect = pygame.Rect(0, 0, CELL_SIZE, CELL_SIZE)
    rects = [rect.move(x * CELL_SIZE, y * CELL_SIZE) for y, x in positions]
    colour = Palette.FOREGROUND_COLOUR if alive else Palette.BACKGROUND_COLOUR

    for rect in rects:
        pygame.draw.rect(screen, colour.value, rect)

    return rects


def paint_board(screen: pygame.Surface):
    paint(screen, _APL.eval("⍸board"), True)
    paint(screen, _APL.eval("⍸~board"), False)


def click(screen: pygame.Surface, event: pygame.event.Event):
    x_, y_ = event.pos
    x = x_ // CELL_SIZE
    y = y_ // CELL_SIZE
    set_status([(y, x)], True)
    pygame.display.update(paint(screen, [(y, x)], True))


def next_gen(screen: pygame.Surface) -> List[pygame.rect.Rect]:
    """Evolve the board to the next generation."""

    _APL.eval("next_board ← ⊃1 board∨.∧3 4=+⌿+⌿¯1 0 1∘.⊖¯1 0 1∘.⌽⊂board")
    new_alive = _APL.eval("⍸new_alive ← next_board∧diff←board≠next_board")
    alive_rects = paint(screen, new_alive, True)
    new_dead = _APL.eval("⍸diff∧~new_alive")
    dead_rects = paint(screen, new_dead, False)
    _APL.eval("board ← next_board")
    return alive_rects + dead_rects


if __name__ == "__main__":
    # Initialise the pygame screen window.
    pygame.init()
    screen: pygame.Surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game of Life (paused)")

    # Initialise the board to be a matrix filled with dead cells.
    _APL.eval("⎕IO ← 0 ⍝ ⎕IO delenda est.")  # Sync ⎕IO with Python's 0-based indexing.
    _APL.eval("board ← ∆⍴0", int(HEIGHT // CELL_SIZE), int(WIDTH // CELL_SIZE))
    screen.fill(Palette.BACKGROUND_COLOUR.value)
    pygame.display.flip()

    dragging, evolving = False, False
    wait_next_gen = 0

    clock = pygame.time.Clock()
    while True:
        clock.tick(FPS)

        if evolving:
            wait_next_gen = (wait_next_gen - 1) % FPS // GENS_PER_SEC
            if not wait_next_gen:
                pygame.display.update(next_gen(screen))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    evolving = not evolving
                    wait_next_gen = FPS // GENS_PER_SEC
                    pygame.display.set_caption("Game of Life" + (
                        "" if evolving else " (paused)"
                    ))

                elif event.key == pygame.K_r:
                    _APL.eval("board ← ?2⍴⍨⍴board")
                    paint_board(screen)
                    pygame.display.flip()

                elif event.key == pygame.K_e:
                    _APL.eval("board ← 0⍴⍨⍴board")
                    paint_board(screen)
                    pygame.display.flip()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT and not evolving:
                    dragging = True
                    click(screen, event)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == pygame.BUTTON_LEFT:
                    dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    click(screen, event)
