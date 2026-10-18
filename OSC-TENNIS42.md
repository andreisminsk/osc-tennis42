# OSC-TENNIS42 — Tennis for Two Recreation

**Spec & Design — v1.0 (2026-10-18)**

Recreation of William Higinbotham's *Tennis for Two* (Brookhaven National Laboratory,
October 18, 1958) using **pygame**, with an authentic DuMont oscilloscope CRT look.

---

## 1. Overview

A two-player, side-view tennis simulation rendered as glowing green vector traces on
a cathode-ray oscilloscope. The entire game is three visual elements — **ground line,
net, ball** — exactly like the original. No sprites, no on-screen score (deviation
noted in §7), no menus.

- **Language:** Python 3.10+
- **Library:** pygame-ce 2.x
- **Target:** 60 FPS, 1280×960 window (scalable), square CRT viewport centered with bezel

## 2. Visual Design (CRT Renderer)

The oscilloscope aesthetic is the core deliverable. Rendered in layers:

| Layer | Description |
|---|---|
| **Phosphor background** | Dark green-black `(10, 20, 12)` base |
| **Traces** | Bright P1-phosphor green `(120, 255, 150)` core, drawn as lines/dots |
| **Persistence** | Offscreen buffer is *faded, not cleared* each frame (×0.85) → motion trails, authentic phosphor decay |
| **Glow/bloom** | Blurred copy of trace buffer additively blended (downscale→upscale trick, cheap) |
| **Graticule** | Faint etched grid `(30, 90, 45)` + center crosshair ticks, drawn over traces |
| **Vignette & bezel** | Static radial darkening + rounded corner mask + dark plastic bezel frame |
| **Flicker** | Per-frame brightness jitter (0.97–1.00 alpha), subtle |

**Pipeline:**
1. Draw game traces to low-res offscreen buffer (512×384) with persistence fade.
2. Blur buffer → additively composite for bloom.
3. Draw graticule overlay.
4. Apply vignette/bezel overlay (pre-rendered once).
5. Scale to window (smooth), apply flicker.

**Colors:** phosphor core `(180, 255, 200)`, trace `(120, 255, 150)`, graticule
`(30, 90, 45)`, background `(10, 20, 12)`.

## 3. Game Design

### 3.1 Court (screen = world)
- Origin at **net base, center screen**. x → right, y → up. Units: meters.
- Court half-length: **11.9 m** each side (real tennis). Net height: **0.91 m**.
- Ground = full-width horizontal line. Net = short vertical line at x=0.
- Ball radius: 0.1 m (drawn as glowing dot with bloom halo).
- **No ceiling** — ball may exit the top of the screen and fall back (authentic).

### 3.2 Controls (keyboard, one player per side)
| Action | Player 1 (left) | Player 2 (right) |
|---|---|---|
| Rotate dial (aim angle) | `A` / `D` | `←` / `→` |
| Hit ball | `Left Shift` | `Right Shift` |
| Reset match | `R` | `R` |
| Toggle graticule | `G` | `G` |
| Quit | `Esc` | `Esc` |

Dial angle range: **10°–80°** above horizontal. A small on-screen dial indicator
(tiny trace arc near each baseline) shows current angle — deviation from original,
kept minimal.

### 3.3 Rules
1. **Hit:** press Hit while the ball is on **your side** of the net, below reach
   (y < 2.5 m), and hit-cooldown (0.25 s) expired. Ball launches at fixed speed
   **17 m/s** at the dial angle toward the opponent.
2. **Net:** ball colliding with the net (crosses x=0 below net top) **rebounds**
   (vx reversed ×0.6). Play continues — no automatic point (physics decides).
3. **Ground bounce:** restitution 0.72, horizontal damping ×0.92 per bounce.
4. **Dead ball:** when post-bounce |vy| < 0.4 m/s and ball is on the ground →
   ball is dead. **Point to the opponent** of the side where it died.
5. **Out:** ball touching ground beyond an end line (|x| > 11.9 m) or exiting the
   screen sides → **point to the opponent of the last hitter**.
6. **Serve:** after a point, the player who **lost** the point serves. Ball is
   frozen at their baseline (x = ±9.9, y = 1.0) until they press Hit.
7. **Match:** first to **11 points, win by 2**. `R` restarts.

### 3.4 Game States
`SERVE → RALLY → POINT_PAUSE (1.2 s, ball keeps bouncing visually) → SERVE … → GAME_OVER`

## 4. Physics (Donner Model 30 emulation)

Semi-implicit Euler, **fixed dt = 1/120 s** with accumulator (deterministic, testable).

- Gravity: `ay = -9.81 m/s²`
- **Air drag (quadratic, as in the original):** `a = -k·|v|·v`, k = 0.012 /m
- Ground bounce & net collision per §3.3
- Pure module: `physics.py` has **no pygame dependency** — fully unit-testable.

## 5. Architecture

```
osc-tennis42/
├── OSC-TENNIS42.md      # this spec
├── requirements.txt     # pygame-ce
├── main.py              # entry point, game loop, state machine
├── settings.py          # all tunable constants (single source of truth)
├── physics.py           # Ball, Court, step() — pure math, no pygame
├── game.py              # match logic: hits, scoring, serving, states
├── crt.py               # CRTRenderer: persistence, bloom, graticule, vignette
├── input.py             # key mapping + edge detection (pressed-this-frame)
└── tests/
    └── test_physics.py  # physics unit tests
```

**Loop:** `input → game.update(dt) → physics.step() → crt.render(traces) → present`

## 6. Testing

- `tests/test_physics.py`:
  - bounce restitution reduces peak height each bounce
  - drag monotonically reduces speed in flight
  - net collision reverses vx below net top; no collision above it
  - dead-ball detection triggers on settling
  - out-of-bounds detection beyond end lines
- Manual checklist: 60 FPS, trails visible, both players can rally ≥ 5 hits.

## 7. Deviations from the 1958 Original (documented, intentional)

1. **Score shown** as small glowing digits in bottom corners — original displayed
   it on the controller box only.
2. **Dial indicator arcs** near baselines — original players felt the knob position.
3. **Fixed hit speed** — 1959 version added a "serve force" button (stretch goal §8).
4. **Keyboard** instead of analog knob + button controllers.

## 8. Stretch Goals (post-v1)

- 1959 mode: force button (hold to charge serve speed), 17″ larger display mode,
  gravity selector (Moon / Mars / Earth — the original's party trick).
- Gamepad support (analog stick = knob).
- Attract mode: AI vs AI demo rally on title screen.
- Barrel-distortion screen curvature shader.

## 9. Milestones

| M | Deliverable | Done when |
|---|---|---|
| **M1** | `physics.py` + tests | all physics tests pass, headless |
| **M2** | `crt.py` | static scene renders with glow, graticule, trails, vignette |
| **M3** | `game.py` + `main.py` + `input.py` | full rally playable, scoring works |
| **M4** | polish | flicker, dial indicators, GAME_OVER screen, balance pass |
