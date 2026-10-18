"""Pure physics for OSC-TENNIS42 — no pygame dependency (unit-testable).

Coordinate system: origin at the net base (court center).
x -> right, y -> up. Units: meters / seconds.
Player 1 defends x < 0 (left), player 2 defends x > 0 (right).

Integration: semi-implicit Euler at a fixed internal substep, wrapped by
step() so callers can use any dt (the game loop feeds a fixed 1/120 s tick).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import settings


@dataclass
class Ball:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)


@dataclass
class StepResult:
    """Events that occurred during one step() call."""

    bounced: bool = False
    bounce_x: float | None = None   # where the ball touched the ground
    hit_net: bool = False
    dead: bool = False
    dead_side: int | None = None    # -1 left / +1 right half where ball settled
    out: bool = False
    out_side: int | None = None     # -1 left / +1 right where ball left play


def place(ball: Ball, x: float, y: float) -> None:
    """Freeze the ball at a position (used for serving)."""
    ball.x, ball.y = x, y
    ball.vx = ball.vy = 0.0


def launch(ball: Ball, speed: float, angle_deg: float, direction: int) -> None:
    """Launch the ball from its current position toward `direction` (+1 / -1)."""
    a = math.radians(angle_deg)
    ball.vx = direction * speed * math.cos(a)
    ball.vy = speed * math.sin(a)


def step(ball: Ball, dt: float) -> StepResult:
    """Advance the simulation by dt seconds. Deterministic; stops early on dead/out."""
    res = StepResult()
    remaining = dt
    while remaining > 1e-9:
        h = min(settings.MAX_SUBSTEP, remaining)
        _substep(ball, h, res)
        remaining -= h
        if res.dead or res.out:
            break
    return res


def _substep(ball: Ball, h: float, res: StepResult) -> None:
    # --- forces: gravity + quadratic air drag a = -k*|v|*v ------------------
    speed = ball.speed
    if speed > 1e-9:
        ax = -settings.DRAG_K * speed * ball.vx
        ay = -settings.GRAVITY - settings.DRAG_K * speed * ball.vy
    else:
        ax, ay = 0.0, -settings.GRAVITY

    prev_x, prev_y = ball.x, ball.y
    ball.vx += ax * h
    ball.vy += ay * h
    ball.x += ball.vx * h
    ball.y += ball.vy * h

    # --- side exit: ball left the visible world ------------------------------
    if abs(ball.x) > settings.WORLD_HALF_WIDTH:
        res.out = True
        res.out_side = 1 if ball.x > 0 else -1
        return

    # --- net: crossed x=0 below the net tape -> rebound -----------------------
    if (prev_x > 0.0 > ball.x) or (prev_x < 0.0 < ball.x):
        t = (0.0 - prev_x) / (ball.x - prev_x)
        y_cross = prev_y + (ball.y - prev_y) * t
        if y_cross < settings.NET_HEIGHT + settings.BALL_RADIUS:
            ball.x = math.copysign(settings.BALL_RADIUS, prev_x)
            ball.y = y_cross
            ball.vx = -ball.vx * settings.NET_RESTITUTION
            res.hit_net = True

    # --- ground contact --------------------------------------------------------
    if ball.y - settings.BALL_RADIUS <= 0.0 and ball.vy < 0.0:
        ball.y = settings.BALL_RADIUS
        ball.vy = -ball.vy * settings.RESTITUTION
        ball.vx *= settings.GROUND_FRICTION
        res.bounced = True
        res.bounce_x = ball.x
        if abs(ball.x) > settings.COURT_HALF_LENGTH:
            res.out = True                    # landed beyond the end line
            res.out_side = 1 if ball.x > 0 else -1
            return
        if abs(ball.vy) < settings.DEAD_VY:   # settled -> dead ball
            res.dead = True
            res.dead_side = 1 if ball.x > 0 else -1

    # --- rolling friction while resting on the ground --------------------------
    if ball.y <= settings.BALL_RADIUS + 1e-4 and abs(ball.vy) < 0.05:
        ball.vx *= max(0.0, 1.0 - settings.ROLL_FRICTION * h)
