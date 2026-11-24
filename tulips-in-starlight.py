"""A little ASCII bouquet in the night sky.

Run with: python tulips-in-starlight.py
Requires only Python's standard library. Press Ctrl+C to leave the animation.
"""
from __future__ import annotations

import math
import os
import random
import shutil
import signal
import sys
import time
from dataclasses import dataclass

# True-colour terminal escape support (including Windows Terminal).
if os.name == "nt":
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass

RESET = "\033[0m"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
HOME = "\033[H"
CLEAR = "\033[2J"

WHITE = (248, 252, 255)
PETAL_TONES = [(152, 213, 255), (204, 174, 255), (255, 177, 212), (145, 238, 215), (255, 221, 147)]
ICE = (185, 232, 255)
GREEN = (36, 222, 126)
MINT = (112, 255, 185)
TEAL = (33, 180, 174)
PAPER = (43, 98, 118)
PAPER_LIT = (91, 161, 166)
GOLD = (255, 202, 81)
PINK = (255, 89, 153)
BLUSH = (255, 166, 192)
STAR = (201, 216, 255)


def rgb(color: tuple[int, int, int]) -> str:
    return f"\033[38;2;{color[0]};{color[1]};{color[2]}m"


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


@dataclass
class Cell:
    depth: float
    char: str
    color: tuple[int, int, int]


class Screen:
    def __init__(self, width: int, height: int, scale: float):
        self.width, self.height, self.scale = width, height, scale
        self.cx = width / 2
        self.floor = height * 0.65
        self.cells: list[list[Cell | None]] = [[None] * width for _ in range(height)]

    def clear(self) -> None:
        self.cells = [[None] * self.width for _ in range(self.height)]

    def xy(self, x: float, y: float) -> tuple[int, int]:
        return round(self.cx + x * self.scale * 1.28), round(self.floor - y * self.scale)

    def put(self, x: float, y: float, z: float, char: str,
            color: tuple[int, int, int]) -> None:
        sx, sy = self.xy(x, y)
        if 0 <= sx < self.width and 0 <= sy < self.height:
            old = self.cells[sy][sx]
            if old is None or z >= old.depth:
                self.cells[sy][sx] = Cell(z, char, color)

    def put_screen(self, x: float, y: float, z: float, char: str,
                   color: tuple[int, int, int]) -> None:
        sx, sy = round(x), round(y)
        if 0 <= sx < self.width and 0 <= sy < self.height:
            old = self.cells[sy][sx]
            if old is None or z >= old.depth:
                self.cells[sy][sx] = Cell(z, char, color)

    def line(self, x1: float, y1: float, x2: float, y2: float, z: float,
             char: str, color: tuple[int, int, int], density: float = 1.0) -> None:
        ax, ay = self.xy(x1, y1)
        bx, by = self.xy(x2, y2)
        steps = max(abs(bx - ax), abs(by - ay), 1)
        for n in range(steps + 1):
            if random.random() <= density:
                q = n / steps
                self.put(x1 + (x2 - x1) * q, y1 + (y2 - y1) * q,
                         z, char, color)

    def render(self) -> str:
        out: list[str] = [HOME]
        for row in self.cells:
            active = None
            for cell in row:
                if cell is None:
                    out.append(" ")
                    active = None
                else:
                    if active != cell.color:
                        out.append(rgb(cell.color))
                        active = cell.color
                    out.append(cell.char)
            out.append(RESET + "\n")
        return "".join(out)


# A broad, domed canopy of blooms: close together like a florist's hand-tied bunch.
FLOWERS = [
    (-11, 15, 3.35), (-4, 17, 3.55), (4, 17, 3.55), (11, 15, 3.35),
    (-18, 10, 3.55), (-10, 12, 3.7), (-2, 13, 3.8), (6, 12, 3.7), (15, 10, 3.55),
    (-23, 5, 3.45), (-15, 7, 3.7), (-7, 8, 3.8), (1, 8, 3.85), (9, 7, 3.8), (17, 6, 3.65), (23, 4, 3.4),
    (-14, 0, 3.45), (-5, -1, 3.65), (5, -1, 3.65), (14, 0, 3.45),
]


def draw_starfield(screen: Screen, stars: list[tuple], now: float) -> None:
    for x, y, phase, speed, size in stars:
        pulse = (math.sin(now * speed + phase) + 1) / 2
        color = mix((62, 76, 113), (255, 239, 204), pulse)
        if size > 0.92 and pulse > 0.78:
            screen.put_screen(x, y, -90, "+", color)
            if pulse > 0.94:
                screen.put_screen(x, y + 1, -90, "|", mix(color, (120, 139, 177), .55))
                screen.put_screen(x - 1, y, -90, "-", mix(color, (120, 139, 177), .55))
        else:
            screen.put_screen(x, y, -90, "*" if size > .72 else ".", color)


def draw_stem(screen: Screen, x: float, head_y: float, base_y: float,
              growth: float, phase: float, now: float, z: float) -> None:
    top = base_y + (head_y - base_y) * growth
    bend = 0.0
    bundle_x = math.sin(phase * 1.7) * .48
    last_x, last_y = bundle_x, base_y
    count = max(2, round((top - base_y) * 4))
    for i in range(1, count + 1):
        u = i / count
        yy = base_y + (top - base_y) * u
        xx = bundle_x * (1 - u) + x * u + bend * math.sin(math.pi * u) + .13 * math.sin(u * 3 + phase) * u
        glyph = "|" if i % 4 else ":"
        shade = mix((12, 111, 75), GREEN, .45 + .45 * math.sin(u * math.pi))
        screen.line(last_x, last_y, xx, yy, z, glyph, shade)
        if i % 3 == 0:
            screen.put(xx + .35, yy, z + .02, "'", MINT)
        last_x, last_y = xx, yy


def draw_leaf(screen: Screen, x: float, y: float, direction: int,
              length: float, phase: float, now: float, growth: float, z: float) -> None:
    if growth <= 0:
        return
    reach = length * growth
    sway = 0.0
    for i in range(1, 23):
        u = i / 22
        lx = x + direction * reach * u + sway * u
        ly = y + .4 + 1.05 * u + .62 * math.sin(math.pi * u)
        half = math.sin(math.pi * u) * .95
        for side in (-1, 0, 1):
            xx = lx + side * half * .72
            yy = ly + side * half * .38
            ch = "/" if direction < 0 else "\\"
            if side == 0:
                ch = "~" if i % 2 else "-"
                color = MINT
            else:
                color = mix((8, 122, 78), GREEN, .55 + .3 * u)
            screen.put(xx, yy, z + .05, ch, color)


def draw_tulip(screen: Screen, x: float, foot_y: float, size: float,
               opened: float, z: float, twinkle: float, accent: tuple[int, int, int]) -> None:
    # A crisp, outlined cup silhouette keeps every bloom distinct in the bunch.
    rows = (
        "  /\\_/\\  ",
        " /#:::#\\ ",
        "/##*#*##\\",
        "|#@###@#|",
        "\\#######/",
        " \\_###_/ ",
    )
    unit = (.62 + .38 * opened) * size / 3.7
    cell_x = unit / (screen.scale * 1.28)
    cell_y = unit / screen.scale
    for r, row in enumerate(rows):
        for c, char in enumerate(row):
            if char == " ":
                continue
            xx = x + (c - 4) * cell_x
            yy = foot_y + (5 - r) * cell_y
            if char in "/\\_|_":
                color = mix(accent, WHITE, .48)
            elif char == "#":
                color = mix(accent, WHITE, .72)
            elif char == "@":
                color = WHITE
            elif char == "*":
                color = mix(GOLD, accent, .28)
            elif char == ":":
                color = accent
            else:
                color = ICE
            screen.put(xx, yy, z + .12 + (5 - r) * .008, char, color)


def draw_baby_breath(screen: Screen, cx: float, now: float, stage: float) -> None:
    # Fine branching sprays peek around and between the tulips.
    for side in (-1, 1):
        root_x = cx + side * 4.2
        root_y = 1.5
        for branch in range(4):
            start = stage(branch * .10 + 2.1)
            length = (3.2 + branch * .45) * start
            bx = root_x + side * branch * .9
            by = root_y + branch * .45
            ex = bx + side * length
            ey = by + 3.5 + branch * .25
            screen.line(bx, by, ex, ey, -1.0, "/" if side < 0 else "\\", TEAL, 1.0)
            for bud in range(1, 5):
                q = bud / 5
                tx = bx + (ex - bx) * q
                ty = by + (ey - by) * q
                for dx, dy in ((0, 0), (-.38, .12), (.38, -.12), (0, .38)):
                    glint = .5 + .5 * math.sin(branch * 2.1 + bud * 1.7)
                    screen.put(tx + dx, ty + dy, -.4,
                               "+" if glint > .82 else ".",
                               mix((142, 202, 225), WHITE, glint))


def draw_wrapper(screen: Screen, now: float, start: float) -> None:
    shown = ease((now - start) / 1.0)
    if shown <= 0:
        return
    # The wrap opens broadly behind the flowers, then narrows into a tied neck.
    top_y, bottom_y = -9.0, -15.6
    for row in range(22):
        v = row / 21
        if v > shown:
            continue
        yy = top_y + (bottom_y - top_y) * v
        half = 11.5 - 7.5 * v
        edge_at = 1.0 - .88 * v
        for col in range(-24, 25):
            u = col / 24
            if abs(u) > edge_at:
                continue
            xx = u * half
            stripe = abs(abs(u) - (.24 + .40 * v)) < .045
            if stripe:
                char = "/" if u < 0 else "\\"
                color = mix(TEAL, PAPER_LIT, .75)
            elif (row + col) % 9 == 0:
                char, color = "'", mix(PAPER_LIT, ICE, .3)
            elif (row + col) % 5 == 0:
                char, color = ":", mix(PAPER, (126, 101, 176), .42)
            else:
                char = "#" if (row + col) % 3 == 0 else "."
                color = mix(PAPER, PAPER_LIT, .25 + .18 * ((row + col) % 4))
            screen.put(xx, yy, -1.5 + v * .03, char, color)
    # Gold piping traces the wide opening and the tapered folded edges.
    for i in range(31):
        v = i / 30 * shown
        yy = top_y + (bottom_y - top_y) * v
        half = 11.5 - 7.5 * v
        for side in (-1, 1):
            screen.put(side * half, yy, -.8, "*" if i % 4 == 0 else ".", GOLD)
    # A pair of crossed bands cinches the narrow end of the wrap.
    band_y = -13.8
    band_v = (top_y - band_y) / (top_y - bottom_y)
    band_half = 11.5 - 7.5 * band_v
    for i in range(31):
        u = i / 30
        xx = -band_half + 2 * band_half * u
        screen.put(xx, band_y + .28 * math.sin(u * math.pi * 2), .15,
                   "=" if i % 2 else "~", GOLD if i % 4 else BLUSH)


def draw_handle(screen: Screen) -> None:
    # The cut stems continue below the paper as a neat, bundled handle.
    for i in range(-5, 6):
        top_x = i * .33
        bottom_x = i * .23
        color = mix((13, 120, 75), GREEN, .45 + .07 * (i + 5))
        screen.line(top_x, -15.45, bottom_x, -18.1, .45,
                    "|" if i % 2 else ":", color)
        screen.put(bottom_x, -18.2, .5, "|", MINT if i % 3 == 0 else color)


def draw_bow(screen: Screen, now: float, start: float) -> None:
    appeared = ease((now - start) / .65)
    if appeared <= 0:
        return
    knot_y = -13.8
    # Satin loops trace broad figure-eights and breathe gently in place.
    for side in (-1, 1):
        for i in range(42):
            a = i / 41 * math.tau
            swell = 0.0
            x = side * (1.2 + (4.0 + swell) * math.sin(a))
            y = knot_y + 2.0 * math.sin(a) * math.cos(a)
            color = mix(PINK, BLUSH, .5 + .5 * math.sin(a))
            screen.put(x, y, 2.2, "@" if i % 4 else "*", color)
            if i % 3 == 0:
                screen.put(x, y + .25, 2.25, "-", GOLD)
    screen.put(-.8, knot_y, 2.6, "<", GOLD)
    screen.put(-.25, knot_y, 2.7, "@", BLUSH)
    screen.put(.25, knot_y, 2.7, "@", PINK)
    screen.put(.8, knot_y, 2.6, ">", GOLD)
    screen.put(0, knot_y + .45, 2.6, "*", WHITE)
    # Long curling tails, edged with gold thread.
    for side in (-1, 1):
        prev = None
        for i in range(22):
            u = i / 21
            x = side * (.55 + 2.5 * u + .28 * math.sin(u * 8))
            y = knot_y - .25 - 3.0 * u + .22 * math.sin(u * 7)
            if prev:
                screen.line(prev[0], prev[1], x, y, 2.15, "~", PINK)
            screen.put(x, y, 2.2, "." if i % 3 else "*", GOLD if i % 4 == 0 else BLUSH)
            prev = (x, y)


def make_stars(width: int, height: int) -> list[tuple]:
    random.seed(9081)
    count = max(160, width * height // 15)
    stars = []
    for _ in range(count):
        stars.append((random.uniform(0, width - 1), random.uniform(0, height - 1),
                      random.random() * math.tau, .6 + random.random() * 2.2,
                      random.random()))
    random.seed()
    return stars


def render_frame(width: int, height: int, now: float,
                 stars: list[tuple]) -> str:
    scale = min((width - 4) / 56, (height - 8) / 40) * .86
    screen = Screen(width, height, max(.55, scale))
    screen.floor = height * .61
    screen.clear()
    draw_starfield(screen, stars, now)
    base_y = -10.1
    # Stems rise first; each closed bud appears at the tip, then blooms only
    # after that stem has reached its full height.
    for i, (x, target_y, size) in enumerate(FLOWERS):
        x *= 1.25
        delay = i * .115
        rise = ease((now - delay) / 1.75)
        if rise <= 0:
            continue
        head_y = base_y + (target_y - base_y) * rise
        draw_stem(screen, x, target_y, base_y, rise, i * .63, now, -2 + (i % 3) * .06)
        leaf_time = max(0.0, now - delay - .35)
        draw_leaf(screen, x * .32, base_y + (target_y - base_y) * .32,
                  -1 if i % 2 else 1, 4.3, i * .8, now,
                  ease(leaf_time / .75), -1.7 + i * .01)
        draw_leaf(screen, x * .62, base_y + (target_y - base_y) * .62,
                  1 if i % 2 else -1, 3.5, i * 1.1, now,
                  ease(max(0.0, now - delay - .62) / .8), -1.6 + i * .01)
        bloom = ease((now - delay - 2.15) / 1.35)
        if rise > .86:
            draw_tulip(screen, x, head_y, size, bloom,
                       1.0 + (i % 4) * .025, .62, PETAL_TONES[i % len(PETAL_TONES)])
    draw_baby_breath(screen, 0, now, lambda cue: ease((now - cue) / .8))
    draw_wrapper(screen, now, 3.2)
    draw_handle(screen)
    draw_bow(screen, now, 4.9)
    return screen.render()


def main() -> None:
    start = time.monotonic()
    stars: list[tuple] = []
    size = None
    fps = 24
    print(CLEAR + HIDE, end="", flush=True)
    try:
        while True:
            term = shutil.get_terminal_size((96, 46))
            width = max(52, min(term.columns - 1, 150))
            height = max(30, min(term.lines - 1, 62))
            current_size = (width, height)
            if current_size != size:
                size = current_size
                stars = make_stars(width, height)
            now = time.monotonic() - start
            frame = render_frame(width, height, now, stars)
            sys.stdout.write(frame)
            sys.stdout.flush()
            time.sleep(1 / fps)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
















