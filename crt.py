"""CRT oscilloscope renderer for OSC-TENNIS42.

Renders glowing vector traces with phosphor persistence, bloom, graticule,
vignette and bezel — the look of a 1958 DuMont lab scope.

Pipeline per frame:
  1. game code draws traces into `buf` (persistent, faded each frame)
  2. present(): compose bg + traces (add) + bloom + graticule + vignette
  3. scale to window, apply flicker, draw bezel
"""
from __future__ import annotations

import math
import random

import pygame

import settings as s


class CRTRenderer:
    def __init__(self, window: pygame.Surface):
        self.win = window
        self.buf = pygame.Surface((s.BUFFER_W, s.BUFFER_H))     # persistent trace buffer
        self.frame = pygame.Surface((s.BUFFER_W, s.BUFFER_H))   # composed output
        self.buf.fill((0, 0, 0))

        # world -> buffer transform
        self.scale = (s.BUFFER_W / 2 - 10) / s.WORLD_HALF_WIDTH  # px per meter
        self.cx = s.BUFFER_W // 2
        self.gy = int(s.BUFFER_H * s.GROUND_SCREEN_FRACTION)

        self._fade = (int(255 * s.PERSISTENCE),) * 3
        self._grat = self._build_graticule()
        self._vig = self._build_vignette()
        self.show_graticule = True

        # screen rect inside the window (4:3, centered, bezel margin)
        m = 70
        w = s.WINDOW_W - 2 * m
        h = int(w * s.BUFFER_H / s.BUFFER_W)
        if h > s.WINDOW_H - 2 * m:
            h = s.WINDOW_H - 2 * m
            w = int(h * s.BUFFER_W / s.BUFFER_H)
        self.screen_rect = pygame.Rect((s.WINDOW_W - w) // 2, (s.WINDOW_H - h) // 2, w, h)
        self._label_font = pygame.font.SysFont('consolas', 16)

    # --- coordinate transform -------------------------------------------------
    def w2b(self, x: float, y: float) -> tuple[float, float]:
        """World meters -> buffer pixels."""
        return (self.cx + x * self.scale, self.gy - y * self.scale)

    # --- trace primitives (game draws these every frame) ----------------------
    def trace_line(self, p1, p2, color=s.COL_TRACE, width=2):
        pygame.draw.line(self.buf, color, p1, p2, width)

    def trace_dot(self, p, radius=3, color=s.COL_TRACE_CORE):
        pygame.draw.circle(self.buf, color, (int(p[0]), int(p[1])), int(radius))

    def trace_polyline(self, pts, color=s.COL_TRACE, width=1):
        if len(pts) >= 2:
            pygame.draw.lines(self.buf, color, False, pts, width)

    # --- 7-segment glowing digits (vector aesthetic, no bitmap font) ----------
    _SEG_MAP = {
        0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc',
        5: 'afgcd', 6: 'afgedc', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg',
    }

    def draw_digit(self, n: int, x: int, y: int, w=10, h=18, color=s.COL_TRACE):
        x2, y2, ym = x + w, y + h, y + h // 2
        segs = {
            'a': ((x + 1, y), (x2 - 1, y)),
            'b': ((x2, y + 1), (x2, ym - 1)),
            'c': ((x2, ym + 1), (x2, y2 - 1)),
            'd': ((x + 1, y2), (x2 - 1, y2)),
            'e': ((x, ym + 1), (x, y2 - 1)),
            'f': ((x, y + 1), (x, ym - 1)),
            'g': ((x + 1, ym), (x2 - 1, ym)),
        }
        for ch in self._SEG_MAP[n % 10]:
            pygame.draw.line(self.buf, color, *segs[ch], 2)

    def draw_number(self, n: int, x: int, y: int, color=s.COL_TRACE) -> int:
        """Draw 0-99 right of x; returns pixel width used."""
        digits = str(max(0, min(99, n)))
        for k, ch in enumerate(digits):
            self.draw_digit(int(ch), x + k * 13, y, color=color)
        return len(digits) * 13

    # --- per-frame composition -------------------------------------------------
    def fade(self):
        """Phosphor persistence: multiply-decay the trace buffer (never clear)."""
        self.buf.fill(self._fade, special_flags=pygame.BLEND_MULT)

    def toggle_graticule(self):
        self.show_graticule = not self.show_graticule

    def present(self):
        f = self.frame
        f.fill(s.COL_BG)
        f.blit(self.buf, (0, 0), special_flags=pygame.BLEND_ADD)

        # bloom: downscale -> upscale -> dim -> additive
        down = pygame.transform.smoothscale(self.buf, (s.BUFFER_W // 4, s.BUFFER_H // 4))
        up = pygame.transform.smoothscale(down, (s.BUFFER_W, s.BUFFER_H))
        up.fill((int(255 * s.GLOW_LEVEL),) * 3, special_flags=pygame.BLEND_MULT)
        f.blit(up, (0, 0), special_flags=pygame.BLEND_ADD)

        if self.show_graticule:
            f.blit(self._grat, (0, 0))
        f.blit(self._vig, (0, 0))

        # window compose: bezel plate -> screen (flicker) -> trim -> label
        self.win.fill(s.COL_BEZEL_DARK)
        bez = self.screen_rect.inflate(28, 28)
        pygame.draw.rect(self.win, s.COL_BEZEL, bez, border_radius=22)
        scaled = pygame.transform.smoothscale(f, self.screen_rect.size)
        scaled.set_alpha(int(255 * random.uniform(s.FLICKER_MIN, 1.0)))
        self.win.blit(scaled, self.screen_rect.topleft)
        pygame.draw.rect(self.win, s.COL_BEZEL_DARK, bez, width=3, border_radius=22)
        pygame.draw.rect(self.win, (0, 0, 0), self.screen_rect.inflate(4, 4), width=2, border_radius=10)
        label = self._label_font.render(
            'TENNIS FOR TWO  \u00b7  BROOKHAVEN NATIONAL LABORATORY  \u00b7  1958',
            True, (95, 100, 96))
        self.win.blit(label, (self.screen_rect.centerx - label.get_width() // 2,
                              self.screen_rect.bottom + 10))

    # --- pre-rendered overlays --------------------------------------------------
    def _build_graticule(self) -> pygame.Surface:
        g = pygame.Surface((s.BUFFER_W, s.BUFFER_H), pygame.SRCALPHA)
        minor, major = 16, 64
        for x in range(0, s.BUFFER_W, minor):
            is_major = x % major == 0
            pygame.draw.line(g, (*s.COL_GRATICULE_MAJOR, 90) if is_major else (*s.COL_GRATICULE, 55),
                             (x, 0), (x, s.BUFFER_H), 1)
        for y in range(0, s.BUFFER_H, minor):
            is_major = y % major == 0
            pygame.draw.line(g, (*s.COL_GRATICULE_MAJOR, 90) if is_major else (*s.COL_GRATICULE, 55),
                             (0, y), (s.BUFFER_W, y), 1)
        c = (s.BUFFER_W // 2, s.BUFFER_H // 2)   # scope center crosshair
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(g, (*s.COL_GRATICULE_MAJOR, 150),
                             (c[0] + dx * 6, c[1] + dy * 6), (c[0] + dx * 18, c[1] + dy * 18), 1)
        return g

    def _build_vignette(self) -> pygame.Surface:
        """Smooth radial darkening (CRT bulb edge) via tiny-alpha smoothscale."""
        tw, th = 12, 9
        tiny = pygame.Surface((tw, th), pygame.SRCALPHA)
        cx, cy = (tw - 1) / 2, (th - 1) / 2
        for ix in range(tw):
            for iy in range(th):
                nx = (ix - cx) / cx if cx else 0.0
                ny = (iy - cy) / cy if cy else 0.0
                d = math.hypot(nx, ny) / math.sqrt(2)          # 0 center .. 1 corner
                a = max(0, min(255, int((d - 0.45) / 0.55 * 235)))
                tiny.set_at((ix, iy), (0, 0, 0, a))
        return pygame.transform.smoothscale(tiny, (s.BUFFER_W, s.BUFFER_H))
