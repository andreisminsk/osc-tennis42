"""Keyboard input with edge detection (pressed-this-frame)."""
from __future__ import annotations

import pygame


class Input:
    def __init__(self):
        self._prev: dict[str, bool] = {}

    def update(self) -> tuple[dict[str, bool], dict[str, bool]]:
        """Returns (held, edges). edges[k] is True only on the frame the key went down."""
        k = pygame.key.get_pressed()
        held = {
            'p1_left':  k[pygame.K_a],
            'p1_right': k[pygame.K_d],
            'p1_hit':   k[pygame.K_LSHIFT],
            'p2_left':  k[pygame.K_LEFT],
            'p2_right': k[pygame.K_RIGHT],
            'p2_hit':   k[pygame.K_RSHIFT],
            'reset':    k[pygame.K_r],
            'grat':     k[pygame.K_g],
            'full':     k[pygame.K_F11],
            'quit':     k[pygame.K_ESCAPE],
        }
        edges = {name: held[name] and not self._prev.get(name, False) for name in held}
        self._prev = held
        return held, edges


def no_edges(held: dict[str, bool]) -> dict[str, bool]:
    """Empty edge set — used after the first fixed tick consumes real edges."""
    return {name: False for name in held}
