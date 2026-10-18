"""OSC-TENNIS42 — Tennis for Two (1958) recreation. Entry point.

Run:  python main.py
"""
from __future__ import annotations

import argparse

import pygame

import bot
import crt
import game
import input
import settings as s


def main() -> None:
    ap = argparse.ArgumentParser(description='Tennis for Two (1958) recreation')
    ap.add_argument('--bot-player', nargs='?', const='1', default=None,
                    choices=('1', '2'), metavar='N',
                    help='computer plays: 1 (default) = Player 1, 2 = Player 2')
    args = ap.parse_args()
    bot_side = int(args.bot_player) - 1 if args.bot_player else None

    pygame.init()
    pygame.display.set_caption('OSC-TENNIS42 \u00b7 Tennis for Two (1958)')
    window = pygame.display.set_mode((s.WINDOW_W, s.WINDOW_H))
    clock = pygame.time.Clock()

    renderer = crt.CRTRenderer(window)
    match = game.Match()
    inp = input.Input()
    bot_ai = bot.Bot(bot_side) if bot_side is not None else None
    if bot_ai is not None:
        print(f'--bot-player: the computer plays Player {bot_side + 1}')

    acc = 0.0
    running = True
    while running:
        # --- real-time frame ---------------------------------------------------
        frame_ms = clock.tick(s.FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

        held, edges = inp.update()
        if edges['quit']:
            running = False
        if edges['grat']:
            renderer.toggle_graticule()

        # --- fixed-timestep simulation (accumulator) ----------------------------
        acc = min(acc + frame_ms, 0.25)          # clamp: avoid spiral of death
        first_tick = True
        while acc >= s.FIXED_DT:
            cur = dict(held) if first_tick else {}
            edg = dict(edges) if first_tick else input.no_edges(held)
            if bot_ai is not None:               # bot overrides its player's keys
                for k, v in bot_ai.update(match).items():
                    cur[k] = v
                    edg[k] = v
            match.update(s.FIXED_DT, cur, edg)
            acc -= s.FIXED_DT
            first_tick = False

        # --- render --------------------------------------------------------------
        renderer.fade()
        game.draw(match, renderer)
        renderer.present()
        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
