"""Unit tests for physics.py (pure module — runs headless, no pygame needed).

Run from the project root:  python -m pytest tests/test_physics.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import physics
import settings
from physics import Ball, step

DT = settings.FIXED_DT


def _run(ball, seconds):
    """Step ball for `seconds`; return event-yielding StepResults; stop on dead/out."""
    results = []
    for _ in range(int(seconds / DT) + 1):
        r = step(ball, DT)
        if r.bounced or r.hit_net or r.dead or r.out:
            results.append(r)
        if r.dead or r.out:
            break
    return results


def test_launch_direction_and_speed():
    b = Ball()
    physics.launch(b, 15.0, 45.0, -1)          # player 2 hits toward the left
    assert b.vx < 0 and b.vy > 0
    assert math.isclose(math.hypot(b.vx, b.vy), 15.0, rel_tol=1e-9)


def test_bounce_reduces_peak_height():
    b = Ball(x=5.0, y=5.0)
    peaks, peak = [], b.y
    for _ in range(int(8.0 / DT)):
        peak = max(peak, b.y)
        r = step(b, DT)
        if r.bounced:
            peaks.append(peak)
            peak = b.y
        if r.dead or r.out:
            break
    assert len(peaks) >= 3
    assert peaks[0] > peaks[1] > peaks[2]


def test_drag_reduces_apex(monkeypatch):
    def apex(k):
        monkeypatch.setattr(settings, "DRAG_K", k)
        b = Ball(x=0.0, y=1.0, vx=5.0, vy=10.0)
        top = b.y
        for _ in range(int(5.0 / DT)):
            step(b, DT)
            top = max(top, b.y)
            if b.vy < 0:
                break
        return top

    assert apex(settings.DRAG_K) < apex(0.0)


def test_net_hit_rebounds_below_tape():
    b = Ball(x=-0.5, y=0.5, vx=5.0, vy=0.0)
    r = step(b, 0.5)
    assert r.hit_net
    assert b.vx < 0 and b.x < 0                # sent back to the hitter's side


def test_no_net_hit_above_tape():
    b = Ball(x=-0.5, y=2.0, vx=5.0, vy=0.0)
    r = step(b, 0.5)
    assert not r.hit_net
    assert b.x > 0


def test_dead_ball_detection():
    for x, side in ((3.0, 1), (-3.0, -1)):
        b = Ball(x=x, y=settings.BALL_RADIUS + 0.01, vy=-0.3)
        r = step(b, 1.0)
        assert r.dead and r.dead_side == side


def test_out_landing_beyond_end_line():
    for x, side in ((12.0, 1), (-12.0, -1)):
        b = Ball(x=x, y=settings.BALL_RADIUS + 0.01, vy=-0.3)
        r = step(b, 1.0)
        assert r.out and r.out_side == side


def test_out_side_exit():
    b = Ball(x=12.4, y=2.0, vx=5.0, vy=0.0)
    r = step(b, 1.0)
    assert r.out and r.out_side == 1


def test_serve_from_baseline_lands_in_court():
    """Balance sanity: a 45-degree serve from the baseline must land in-bounds."""
    b = Ball(x=-settings.SERVE_X, y=settings.SERVE_Y)
    physics.launch(b, settings.HIT_SPEED, 45.0, 1)
    results = _run(b, 6.0)
    bounces = [r for r in results if r.bounced]
    assert bounces, "serve never landed"
    assert abs(bounces[0].bounce_x) <= settings.COURT_HALF_LENGTH, (
        f"45-degree serve overshot: landed at x={bounces[0].bounce_x:.2f}"
    )


def test_deterministic():
    a, b = Ball(x=-9.9, y=1.0), Ball(x=-9.9, y=1.0)
    physics.launch(a, settings.HIT_SPEED, 40.0, 1)
    physics.launch(b, settings.HIT_SPEED, 40.0, 1)
    for _ in range(int(3.0 / DT)):
        step(a, DT)
        step(b, DT)
    assert (a.x, a.y, a.vx, a.vy) == (b.x, b.y, b.vx, b.vy)
