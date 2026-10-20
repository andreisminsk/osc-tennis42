"""Match logic for OSC-TENNIS42: states, hits, scoring, serving, scene drawing."""
from __future__ import annotations

import math

import pygame

import physics
import settings as s

SERVE, RALLY, POINT_PAUSE, GAME_OVER = 0, 1, 2, 3


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Match:
    def __init__(self):
        self.reset()

    def reset(self):
        self.ball = physics.Ball()
        self.scores = [0, 0]
        self.server = 0
        self.last_hitter: int | None = None
        self.state = SERVE
        self.timer = 0.0
        self.angles = [45.0, 45.0]
        self.cool = [0.0, 0.0]
        self.events: list[str] = []      # 'serve' | 'hit' | 'net' | 'bounce' | 'dead' | 'out'
        self._place_serve()

    def _place_serve(self):
        side = -1 if self.server == 0 else 1
        physics.place(self.ball, side * s.SERVE_X, s.SERVE_Y)

    # ------------------------------------------------------------------ update
    def update(self, dt: float, cur: dict, edges: dict):
        self._rotate_dials(dt, cur)
        self.cool = [max(0.0, c - dt) for c in self.cool]

        if edges.get('reset'):
            self.reset()
            return

        if self.state == SERVE:
            if edges.get(f'p{self.server + 1}_hit'):
                side = 1 if self.server == 0 else -1    # serve travels toward the net
                physics.launch(self.ball, s.HIT_SPEED, self.angles[self.server], side)
                self.last_hitter = self.server
                self.cool[self.server] = s.HIT_COOLDOWN
                self.state = RALLY
                self.events.append('serve')

        elif self.state == RALLY:
            res = physics.step(self.ball, dt)
            if res.hit_net:
                self.events.append('net')
            if res.bounced:
                self.events.append('bounce')
            self._apply_result(res)
            if self.state == RALLY:                      # still live -> allow hits
                for i in (0, 1):
                    if edges.get(f'p{i + 1}_hit') and self._can_hit(i):
                        side = 1 if i == 0 else -1      # hit travels over the net
                        physics.launch(self.ball, s.HIT_SPEED, self.angles[i], side)
                        self.last_hitter = i
                        self.cool[i] = s.HIT_COOLDOWN
                        self.events.append('hit')

        elif self.state == POINT_PAUSE:
            self.timer -= dt
            physics.step(self.ball, dt)      # ball keeps rolling/bouncing (spec §3.4)
            if self.timer <= 0.0:
                if self._match_over():
                    self.state = GAME_OVER
                else:
                    self.state = SERVE
                    self._place_serve()

        # GAME_OVER: frozen until 'reset'

    def _rotate_dials(self, dt, cur):
        for i, (lk, rk) in enumerate((('p1_left', 'p1_right'), ('p2_left', 'p2_right'))):
            d = (1 if cur.get(rk) else 0) - (1 if cur.get(lk) else 0)
            self.angles[i] = _clamp(self.angles[i] + d * s.ANGLE_SPEED * dt,
                                    s.ANGLE_MIN, s.ANGLE_MAX)

    def _can_hit(self, i: int) -> bool:
        side = -1 if i == 0 else 1
        return self.ball.x * side > 0.0 and self.ball.y < s.HIT_REACH and self.cool[i] <= 0.0

    def _apply_result(self, res: physics.StepResult):
        if res.out:
            self.events.append('out')
            self._award(1 - self.last_hitter)            # opponent of the last hitter
        elif res.dead:
            self.events.append('dead')
            loser = 0 if res.dead_side < 0 else 1        # ball died on their side
            self._award(1 - loser)

    def _award(self, i: int):
        self.scores[i] += 1
        self.server = 1 - i                              # loser of the point serves
        self.last_hitter = None
        self.state = POINT_PAUSE
        self.timer = s.POINT_PAUSE

    def _match_over(self) -> bool:
        a, b = self.scores
        return max(a, b) >= s.TARGET_SCORE and abs(a - b) >= 2

    @property
    def winner(self) -> int:
        return 0 if self.scores[0] > self.scores[1] else 1


# ---------------------------------------------------------------------- drawing
def draw(match: Match, crt):
    """Emit the scene as vector traces into the CRT buffer."""
    # ground line across the full screen
    crt.trace_line(crt.w2b(-s.WORLD_HALF_WIDTH, 0), crt.w2b(s.WORLD_HALF_WIDTH, 0), width=2)
    # end-line ticks
    for sx in (-1, 1):
        x = sx * s.COURT_HALF_LENGTH
        crt.trace_line(crt.w2b(x, 0), crt.w2b(x, 0.7), width=2)
    # net
    crt.trace_line(crt.w2b(0, 0), crt.w2b(0, s.NET_HEIGHT), width=2)

    # dial indicators: faint protractor arc + bright angle tick at each baseline
    for i, sx in ((0, -1), (1, 1)):
        bx = sx * s.SERVE_X
        d = 1 if i == 0 else -1              # shot direction: both dials face the net
        pts = [crt.w2b(bx + d * 1.1 * math.cos(math.radians(a)), 1.1 * math.sin(math.radians(a)))
               for a in range(int(s.ANGLE_MIN), int(s.ANGLE_MAX) + 1, 5)]
        crt.trace_polyline(pts, color=s.COL_GRATICULE_MAJOR, width=1)
        a = math.radians(match.angles[i])
        p1 = crt.w2b(bx + d * 0.85 * math.cos(a), 0.85 * math.sin(a))
        p2 = crt.w2b(bx + d * 1.35 * math.cos(a), 1.35 * math.sin(a))
        crt.trace_line(p1, p2, color=s.COL_TRACE, width=2)

    # ball (glowing dot; bloom adds the phosphor halo)
    b = match.ball
    crt.trace_dot(crt.w2b(b.x, b.y), radius=max(3, s.BALL_RADIUS * crt.scale))

    # scores: 7-seg digits in the bottom corners; winner's blinks on game over
    y = s.BUFFER_H - 26
    on = match.state != GAME_OVER or (pygame.time.get_ticks() // 400) % 2 == 0
    for i, x in ((0, 10), (1, s.BUFFER_W - 10 - 13 * len(str(max(1, match.scores[1]))))):
        if i == match.winner and match.state == GAME_OVER and not on:
            continue
        crt.draw_number(match.scores[i], x, y)
