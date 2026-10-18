"""All tunable constants for OSC-TENNIS42 — single source of truth."""

# --- Window / render --------------------------------------------------------
WINDOW_W = 1280
WINDOW_H = 960
BUFFER_W = 512              # low-res CRT trace buffer (4:3, like a scope tube)
BUFFER_H = 384
FPS = 60

# --- World (meters; origin = net base, x right, y up) -----------------------
COURT_HALF_LENGTH = 11.9    # baseline distance from the net (real tennis)
NET_HEIGHT = 0.91
BALL_RADIUS = 0.10
WORLD_HALF_WIDTH = 12.5     # screen edge in world units (side-exit boundary)
GROUND_SCREEN_FRACTION = 0.75   # ground line height on the buffer (0=top, 1=bottom)

# --- Physics (Donner Model 30 emulation) ------------------------------------
GRAVITY = 9.81
DRAG_K = 0.012              # quadratic air drag: a = -k * |v| * v
RESTITUTION = 0.72          # vertical energy kept per ground bounce
GROUND_FRICTION = 0.92      # horizontal damping per ground bounce
NET_RESTITUTION = 0.60      # vx kept when the ball rebounds off the net
ROLL_FRICTION = 1.5         # /s, applied while the ball rests on the ground
FIXED_DT = 1.0 / 120.0      # simulation tick (accumulator lives in main)
MAX_SUBSTEP = 1.0 / 240.0   # internal collision-safe substep

# --- Gameplay ----------------------------------------------------------------
HIT_SPEED = 15.0            # fixed launch speed (m/s)
HIT_REACH = 2.5             # max ball height (m) at which a hit is allowed
HIT_COOLDOWN = 0.25         # s between hits (per player)
ANGLE_MIN = 10.0            # dial range, degrees above horizontal
ANGLE_MAX = 80.0
ANGLE_SPEED = 60.0          # dial rotation while key held (deg/s)
SERVE_X = 9.9               # serve baseline distance from the net
SERVE_Y = 1.0
DEAD_VY = 0.4               # post-bounce |vy| below this -> ball is dead
POINT_PAUSE = 1.2           # s after a point before the next serve
TARGET_SCORE = 11           # win by 2

# --- CRT palette / look -------------------------------------------------------
COL_BG = (10, 20, 12)            # phosphor screen background
COL_TRACE = (120, 255, 150)      # P1 phosphor trace
COL_TRACE_CORE = (185, 255, 205) # hot core (ball, bright dots)
COL_GRATICULE = (30, 90, 45)
COL_GRATICULE_MAJOR = (45, 120, 60)
COL_BEZEL = (30, 30, 33)
COL_BEZEL_DARK = (14, 14, 16)

PERSISTENCE = 0.85           # trace decay per frame (higher = longer trails)
GLOW_LEVEL = 0.45            # bloom intensity (multiplier on blurred copy)
FLICKER_MIN = 0.97           # per-frame brightness jitter lower bound
