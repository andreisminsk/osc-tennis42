"""Computer-controlled player for OSC-TENNIS42.

The bot 'thinks' with the same physics engine that runs the game — a nod to the
Donner Model 30 analog computer the original ran on: when it must choose a shot,
it forward-simulates a fan of candidate dial angles and picks the one whose first
bounce lands closest to its target depth in the opponent's court, rejecting
shots that would clip the net or land out.

update(match) is called once per fixed simulation tick (1/120 s) and returns the
keys the bot presses this tick: {'pN_left', 'pN_right', 'pN_hit'}. The hit key is
a one-tick pulse so the game's edge detection fires exactly once.
"""
from __future__ import annotations

import random

import game
import physics
import settings as s

_IDEAL_MIN, _IDEAL_MAX = 5.0, 10.5     # preferred landing depth past the net (m)


class Bot:
    """Controls one player: 0 = left/P1, 1 = right/P2."""

    def __init__(self, player: int = 0):
        self.player = player
        self.side = -1 if player == 0 else 1
        self.target = 45.0             # dial angle currently rotating toward
        self._replan = True            # a new shot angle needs to be chosen

    # ------------------------------------------------------------------ api
    def update(self, match: game.Match) -> dict[str, bool]:
        n = self.player + 1
        lk, rk, hk = f'p{n}_left', f'p{n}_right', f'p{n}_hit'
        keys = {lk: False, rk: False, hk: False}
        me, b = self.player, match.ball
        angle = match.angles[me]
        on_my_side = b.x * self.side > 0.0

        if match.state == game.SERVE:
            if match.server == me:
                if self._replan:
                    self.target = self._pick(b)
                    self._replan = False
                self._rotate(keys, lk, rk, angle)
                if abs(angle - self.target) < 1.5:
                    keys[hk] = True                    # serve!
            return keys

        if match.state != game.RALLY:                  # POINT_PAUSE / GAME_OVER
            self._replan = True
            return keys

        if not on_my_side:                             # ball is with the opponent
            self._replan = True                        # ...plan the return
            return keys

        hittable = b.y < s.HIT_REACH and match.cool[me] <= 0.0

        # Choose the shot once the ball is committed to our side (descending or
        # already within reach), then rotate the dial toward the chosen angle.
        if self._replan and (hittable or b.vy < 0.0):
            self.target = self._pick(b)
            self._replan = False
        self._rotate(keys, lk, rk, angle)

        if hittable:
            aimed = abs(angle - self.target) < 2.0
            desperate = b.y < 0.55 and b.vy < 0.0             # about to die — swing!
            leaving = b.vy > 0.0 and b.y > s.HIT_REACH - 0.7  # volley before it escapes
            if aimed or desperate or leaving:
                keys[hk] = True
                self._replan = True
        return keys

    # ------------------------------------------------------------ internals
    def _rotate(self, keys: dict[str, bool], lk: str, rk: str, angle: float) -> None:
        diff = self.target - angle
        if diff > 0.5:
            keys[rk] = True                   # dial up
        elif diff < -0.5:
            keys[lk] = True                   # dial down

    def _pick(self, b: physics.Ball) -> float:
        """Forward-simulate candidate angles; return the best dial setting."""
        ideal = random.uniform(_IDEAL_MIN, _IDEAL_MAX)   # vary the landing depth
        best, best_score = 45.0, float('-inf')
        for a in range(int(s.ANGLE_MIN) + 5, int(s.ANGLE_MAX), 5):    # 15..75 step 5
            sim = physics.Ball(b.x, b.y, b.vx, b.vy)
            physics.launch(sim, s.HIT_SPEED, float(a), -self.side)    # toward opponent
            score = self._landing_score(sim, ideal)
            if score > best_score:
                best_score, best = score, float(a)
        return best

    @staticmethod
    def _landing_score(sim: physics.Ball, ideal: float) -> float:
        """Simulate one shot; score its first landing (higher = better)."""
        for _ in range(int(6.0 / s.FIXED_DT)):
            r = physics.step(sim, s.FIXED_DT)
            if r.hit_net:
                return -1000.0                            # clipped the tape
            if r.out:
                return -500.0 - abs(sim.x)                # out; less far = less bad
            if r.bounced:
                d = abs(r.bounce_x)
                if d <= s.COURT_HALF_LENGTH - 0.2:
                    return 100.0 - abs(ideal - d)         # in: near `ideal` is best
                return -400.0 + d                         # just past the end line
        return -1000.0                                    # never landed
