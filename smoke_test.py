"""Headless smoke test — run as a subprocess:  python smoke_test.py

Two bots rally: server always serves; receiver occasionally 'sleeps' so points
can end. Verifies serve direction, multi-hit rallies, scoring, and rendering.
"""
import os, random, sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
window = pygame.display.set_mode((1280, 960))

import bot as botmod
import crt, game, settings as s

# sanity: the loaded game module must contain the fixed serve line
import inspect
src = inspect.getsource(game.Match.update)
assert 'side = 1 if self.server == 0 else -1' in src, 'STALE game module loaded!'

renderer = crt.CRTRenderer(window)
match = game.Match()
random.seed(42)
use_bot = '--bot' in sys.argv              # --bot: P1 played by the Bot AI
bot_ai = botmod.Bot(0) if use_bot else None
if use_bot:
    print('mode: Bot (P1) vs scripted hitter (P2)', flush=True)

KEYS = ('p1_left', 'p1_right', 'p1_hit', 'p2_left', 'p2_right',
        'p2_hit', 'reset', 'grat', 'quit')
held = {k: False for k in KEYS}
prev, prev_state = {}, None
sleeping = [False, False]
rally_sizes, cur_rally = [], 0
end_reasons = {'dead': 0, 'out': 0}
serve_checks = []          # (server, actual vx sign, matches expected)

for f in range(14400):                          # up to 120 sim-seconds
    if match.state == game.SERVE and prev_state != game.SERVE:
        sleeping[match.server] = False          # server always serves
        sleeping[1 - match.server] = random.random() < 0.5

    if bot_ai is not None:                      # Bot drives all of P1's keys
        held.update(bot_ai.update(match))

    if match.state == game.SERVE:
        if bot_ai is None or match.server != 0:
            held[f'p{match.server + 1}_hit'] = True
    elif match.state == game.RALLY:
        if bot_ai is None:
            held['p1_hit'] = (match.ball.x < 0 and match.ball.y < s.HIT_REACH
                              and match.cool[0] <= 0 and not sleeping[0])
        held['p2_hit'] = (match.ball.x > 0 and match.ball.y < s.HIT_REACH
                          and match.cool[1] <= 0 and not sleeping[1])
    else:
        held['p2_hit'] = False
        if bot_ai is None:
            held['p1_hit'] = False

    if bot_ai is None:
        match.angles[0] = random.uniform(15, 75)
    match.angles[1] = random.uniform(15, 75)

    edges = {k: held[k] and not prev.get(k, False) for k in held}
    n0 = len(match.events)
    match.update(s.FIXED_DT, held, edges)
    new = match.events[n0:]

    if 'serve' in new:
        expected = 1 if match.server == 0 else -1   # toward the net
        actual = 1 if match.ball.vx > 0 else -1
        serve_checks.append((match.server, actual, actual == expected))
    cur_rally += sum(e in ('serve', 'hit') for e in new)
    for e in new:
        if e in end_reasons:
            end_reasons[e] += 1
    if any(e in ('dead', 'out') for e in new):
        rally_sizes.append(cur_rally)
        cur_rally = 0

    if f % 10 == 0:                     # render sparsely — renderer already proven
        renderer.fade()
        game.draw(match, renderer)
        renderer.present()
    prev, prev_state = dict(held), match.state
    if f % 600 == 0:
        print(f'  tick {f}: state={match.state} scores={match.scores}', flush=True)

    if match.state == game.GAME_OVER:
        print(f'GAME_OVER at tick {f} — winner: P{match.winner + 1}')
        break

print('scores:', match.scores, '| points:', len(rally_sizes))
print('point ends:', end_reasons)
print('hits per rally:', rally_sizes)
print('max rally:', max(rally_sizes) if rally_sizes else 0)
print('serves (server, vx sign, ok):', serve_checks)

points_ended = end_reasons['dead'] + end_reasons['out']
ok = (all(c[2] for c in serve_checks)          # every serve travels toward the net
      and points_ended >= 3                    # points actually conclude
      and sum(match.scores) == points_ended    # every conclusion awarded a point
      and max(rally_sizes) >= 3)               # multi-hit rallies occur
print('SMOKE TEST ' + ('PASS' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
