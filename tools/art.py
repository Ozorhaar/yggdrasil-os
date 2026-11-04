#!/usr/bin/env python3
"""Yggdrasil OS artwork generator.

Produces every SVG used by the theme (logo, wallpapers, rune glyphs, splash
pieces) from code, so the art is original and easy to tweak. Run:

    python3 tools/art.py out_dir

then render with rsvg-convert (see tools/render.sh).
"""
import math
import os
import random
import sys

# ---------------------------------------------------------------- palette
NIGHT = "#0b1220"
NIGHT2 = "#121b2e"
IRON = "#2a2f36"
OAK = "#6b4a2b"
GOLD = "#c8a25a"
GOLD_HI = "#ecd08f"
FROST = "#8fc4e0"
EMBER = "#e0703a"
BONE = "#e8dcc4"

# ------------------------------------------------------------ rune glyphs
# Elder Futhark runes as straight strokes in a 0..1 tall box (width varies).
RUNES = {
    "Y": (0.7, [[(0.30, 0.08), (0.05, 0.33), (0.30, 0.58)],
                [(0.40, 0.42), (0.65, 0.67), (0.40, 0.92)]]),          # jera
    "G": (0.6, [[(0.05, 0.08), (0.55, 0.92)], [(0.55, 0.08), (0.05, 0.92)]]),  # gebo
    "D": (0.75, [[(0.05, 0.05), (0.05, 0.95)], [(0.70, 0.05), (0.70, 0.95)],
                 [(0.05, 0.05), (0.70, 0.95)], [(0.05, 0.95), (0.70, 0.05)]]),  # dagaz
    "R": (0.55, [[(0.08, 0.95), (0.08, 0.05), (0.45, 0.25), (0.08, 0.47), (0.50, 0.95)]]),  # raido
    "A": (0.55, [[(0.08, 0.95), (0.08, 0.05)], [(0.08, 0.05), (0.48, 0.28)],
                 [(0.08, 0.30), (0.48, 0.53)]]),                      # ansuz
    "S": (0.55, [[(0.45, 0.05), (0.08, 0.42), (0.45, 0.58), (0.08, 0.95)]]),  # sowilo
    "I": (0.2, [[(0.10, 0.05), (0.10, 0.95)]]),                          # isa
    "L": (0.55, [[(0.08, 0.95), (0.08, 0.05), (0.48, 0.30)]]),            # laguz
    "F": (0.55, [[(0.08, 0.95), (0.08, 0.05)], [(0.08, 0.10), (0.48, 0.30)],
                 [(0.08, 0.35), (0.48, 0.55)]]),                      # fehu
    "U": (0.6, [[(0.08, 0.95), (0.08, 0.05), (0.52, 0.30), (0.52, 0.95)]]),  # uruz
    "TH": (0.55, [[(0.08, 0.05), (0.08, 0.95)], [(0.08, 0.25), (0.48, 0.50), (0.08, 0.75)]]),  # thurisaz
    "K": (0.45, [[(0.40, 0.10), (0.08, 0.50), (0.40, 0.90)]]),            # kaunan
    "W": (0.55, [[(0.08, 0.95), (0.08, 0.05), (0.45, 0.25), (0.08, 0.45)]]),  # wunjo
    "H": (0.6, [[(0.08, 0.05), (0.08, 0.95)], [(0.52, 0.05), (0.52, 0.95)],
                [(0.08, 0.30), (0.52, 0.55)]]),                       # hagalaz
    "N": (0.5, [[(0.25, 0.05), (0.25, 0.95)], [(0.05, 0.35), (0.45, 0.60)]]),  # naudiz
    "P": (0.6, [[(0.45, 0.05), (0.10, 0.25), (0.10, 0.75), (0.45, 0.95)],
                [(0.10, 0.25), (0.45, 0.45)], [(0.10, 0.75), (0.45, 0.55)]]),  # perth
    "E": (0.6, [[(0.08, 0.95), (0.08, 0.05), (0.30, 0.30), (0.52, 0.05), (0.52, 0.95)]]),  # ehwaz
    "M": (0.6, [[(0.08, 0.95), (0.08, 0.05), (0.52, 0.40)], [(0.52, 0.95), (0.52, 0.05), (0.08, 0.40)]]),  # mannaz
    "B": (0.55, [[(0.08, 0.05), (0.08, 0.95)], [(0.08, 0.05), (0.45, 0.27), (0.08, 0.50), (0.45, 0.73), (0.08, 0.95)]]),  # berkanan
}
NAME_RUNES = ["Y", "G", "G", "D", "R", "A", "S", "I", "L"]
# A decorative band: the futhark letters minus a few that carry modern
# political baggage when used alone (othala, tiwaz, algiz are left out).
BAND_RUNES = ["F", "U", "TH", "A", "R", "K", "G", "W", "H", "N", "I", "Y",
              "P", "S", "B", "E", "M", "L", "D"]


def rune_path(key, x, y, h):
    """Return (svg path d, width) for rune `key` with top-left x,y, height h."""
    w, strokes = RUNES[key]
    parts = []
    for s in strokes:
        pts = " L ".join(f"{x + px * h:.2f},{y + py * h:.2f}" for px, py in s)
        parts.append("M " + pts)
    return " ".join(parts), w * h


def rune_text(keys, x, y, h, gap=0.25):
    d_all, cx = [], x
    for k in keys:
        d, w = rune_path(k, cx, y, h)
        d_all.append(d)
        cx += w + gap * h
    return " ".join(d_all), cx - x - gap * h


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><defs>{defs}</defs>{body}</svg>\n')


# -------------------------------------------------------------- the tree
def tree_paths(cx, cy, scale, seed=7, crown_depth=7, root_depth=5):
    """World-tree branches (up) and roots (down) as lists of (d, width)."""
    rnd = random.Random(seed)
    out = []

    def branch(x, y, ang, ln, wd, depth, spread, droop):
        if depth == 0 or ln < 2:
            return
        x2 = x + math.cos(ang) * ln
        y2 = y + math.sin(ang) * ln
        # gentle curve via a control point offset sideways
        mx = (x + x2) / 2 + math.cos(ang + math.pi / 2) * ln * rnd.uniform(-0.15, 0.15)
        my = (y + y2) / 2 + math.sin(ang + math.pi / 2) * ln * rnd.uniform(-0.15, 0.15)
        out.append((f"M {x:.1f},{y:.1f} Q {mx:.1f},{my:.1f} {x2:.1f},{y2:.1f}", wd))
        kids = 2 if depth > 2 else rnd.choice([2, 3])
        for i in range(kids):
            t = (i / (kids - 1) - 0.5) if kids > 1 else 0
            a = ang + t * spread + rnd.uniform(-0.12, 0.12) + droop
            branch(x2, y2, a, ln * rnd.uniform(0.68, 0.80), wd * 0.68, depth - 1,
                   spread * 0.95, droop)

    trunk_top = cy - 40 * scale
    trunk_bot = cy + 40 * scale
    out.append((f"M {cx:.1f},{trunk_bot:.1f} L {cx:.1f},{trunk_top:.1f}", 26 * scale))
    # crown: several main limbs fanning upward
    for a in (-150, -128, -105, -90, -75, -52, -30):
        rad = math.radians(a)
        branch(cx, trunk_top, rad, 95 * scale, 14 * scale, crown_depth, 1.15, 0)
    # roots: mirrored, flatter
    for a in (150, 128, 105, 90, 75, 52, 30):
        rad = math.radians(a)
        branch(cx, trunk_bot, rad, 70 * scale, 12 * scale, root_depth, 1.0, 0)
    return out


def tree_group(cx, cy, scale, color, seed=7, glow=True, crown_depth=7, root_depth=5):
    paths = tree_paths(cx, cy, scale, seed, crown_depth, root_depth)
    g = "".join(f'<path d="{d}" stroke-width="{w:.2f}"/>' for d, w in paths)
    flt = ' filter="url(#glow)"' if glow else ""
    return (f'<g fill="none" stroke="{color}" stroke-linecap="round" '
            f'stroke-linejoin="round"{flt}>{g}</g>')


GLOW = ('<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="{s}" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


# --------------------------------------------------------------- the logo
def logo(size=512, color=GOLD, bg=None, band=True):
    c = size / 2
    r_out = size * 0.47
    r_in = size * 0.36
    defs = GLOW.format(s=size * 0.006)
    body = ""
    if bg:
        body += f'<circle cx="{c}" cy="{c}" r="{r_out}" fill="{bg}"/>'
    body += (f'<circle cx="{c}" cy="{c}" r="{r_out}" fill="none" stroke="{color}" '
             f'stroke-width="{size*0.018}"/>')
    body += (f'<circle cx="{c}" cy="{c}" r="{r_in}" fill="none" stroke="{color}" '
             f'stroke-width="{size*0.010}"/>')
    if band:
        # runes marching round the band between the two rings
        n = len(BAND_RUNES) + 1
        rh = (r_out - r_in) * 0.55
        for i, k in enumerate(BAND_RUNES):
            ang = 360 * i / n - 90 + 360 / n / 2
            d, w = rune_path(k, -RUNES[k][0] * rh / 2, -rh / 2, rh)
            rm = (r_out + r_in) / 2
            body += (f'<path d="{d}" transform="translate({c},{c}) rotate({ang + 90}) '
                     f'translate(0,{-rm})" fill="none" stroke="{color}" '
                     f'stroke-width="{size*0.008}" stroke-linecap="round" stroke-linejoin="round"/>')
        # a knot dot where the band starts/ends
        body += (f'<circle cx="{c}" cy="{c - (r_out + r_in) / 2}" r="{size*0.012}" fill="{color}"/>')
    sc = size / 512 * 0.52
    body += f'<clipPath id="inner"><circle cx="{c}" cy="{c}" r="{r_in - size*0.02}"/></clipPath>'
    body += f'<g clip-path="url(#inner)">{tree_group(c, c + size*0.01, sc, color, glow=False, crown_depth=6, root_depth=4)}</g>'
    return svg(size, size, body, defs)


def logo_symbolic(size=64):
    """World tree for small sizes (app-menu button, tray): a full leafy crown,
    trunk and spreading roots, so it reads as a tree even at 22 px."""
    k = size / 64
    crown = "".join(f'<circle cx="{x*k}" cy="{y*k}" r="{r*k}"/>' for x, y, r in
                    ((32, 21, 11), (21, 25, 8.5), (43, 25, 8.5), (25, 16, 7.5), (39, 16, 7.5), (32, 13, 7)))
    trunk = (f'<path d="M {29*k},{29*k} L {35*k},{29*k} L {34.5*k},{44*k} L {29.5*k},{44*k} Z"/>')
    roots = (f'<path d="M {32*k},{43*k} Q {26*k},{47*k} {20*k},{51*k} M {32*k},{43*k} Q {38*k},{47*k} {44*k},{51*k} '
             f'M {32*k},{44*k} L {32*k},{53*k}" fill="none" stroke="{GOLD}" stroke-width="{3.2*k}" stroke-linecap="round"/>')
    body = (f'<circle cx="{32*k}" cy="{32*k}" r="{29*k}" fill="{NIGHT}" stroke="{GOLD}" stroke-width="{3.5*k}"/>'
            f'<g fill="{GOLD}">{crown}{trunk}</g>{roots}')
    return svg(size, size, body)


def shield_icon(fill, glyph, size=64):
    """Login/power buttons: a round longship shield with a carved glyph."""
    k = size / 64
    body = (f'<circle cx="{32*k}" cy="{32*k}" r="{29*k}" fill="{fill}" stroke="{NIGHT}" stroke-width="{3*k}"/>'
            f'<circle cx="{32*k}" cy="{32*k}" r="{24.5*k}" fill="none" stroke="#000" stroke-opacity="0.18" stroke-width="{1.5*k}"/>'
            f'<g transform="scale({k})" fill="none" stroke="#141a26" stroke-width="5" '
            f'stroke-linecap="square" stroke-linejoin="miter">{glyph}</g>')
    return svg(size, size, body)


def _arc(cx, cy, r, a0, a1, step=45):
    pts, a = [], a0
    while a <= a1 + 0.01:
        pts.append((cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))))
        a += step
    return pts


def power_icons():
    """name -> svg for the power/login action icons."""
    pl = lambda pts: "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    moon = ('<path d="M 38,15 A 17 17 0 1 0 47,42 A 13 13 0 1 1 38,15 Z" fill="#141a26" stroke="none"/>')
    ring = _arc(32, 33, 14, -30, 240, 45)  # angular, carved circle
    restart = (f'<path d="{pl(ring)}"/>'
               f'<path d="{pl([(ring[-1][0] - 8, ring[-1][1] - 2), ring[-1], (ring[-1][0] + 2, ring[-1][1] + 9)])}"/>')
    pring = _arc(32, 35, 14, -50, 230, 40)
    power = f'<path d="{pl(pring)}"/><path d="M 32,14 L 32,32"/>'
    other = '<path d="M 19,23 L 45,19"/><path d="M 19,34 L 45,30"/><path d="M 19,45 L 45,41"/>'
    sleep = shield_icon(FROST, moon)
    return {
        "system-suspend": sleep,
        "system-suspend-hibernate": sleep,
        "system-reboot": shield_icon(GOLD, restart),
        "system-shutdown": shield_icon(EMBER, power),
        "system-user-list": shield_icon(BONE, other),
    }


# -------------------------------------------------------------- landscape
def ridge(rnd, w, base, amp, rough, n=257):
    pts = [base + rnd.uniform(-amp, amp) for _ in range(2)]
    pts = [pts[0], pts[1]]
    # midpoint displacement
    arr = [None] * n
    arr[0], arr[-1] = pts
    step, a = n - 1, amp
    while step > 1:
        half = step // 2
        for i in range(half, n - 1, step):
            arr[i] = (arr[i - half] + arr[i + half]) / 2 + rnd.uniform(-a, a)
        step = half
        a *= rough
    return [(w * i / (n - 1), y) for i, y in enumerate(arr)]


def poly(pts, w, h, fill, extra=""):
    d = "M 0,{h} ".format(h=h) + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts) + f" L {w},{h} Z"
    return f'<path d="{d}" fill="{fill}" {extra}/>'


def stars(rnd, w, h, n, ymax):
    s = ""
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, ymax) ** 1.0
        r = rnd.choice([0.8, 1, 1.2, 1.6, 2.2])
        o = rnd.uniform(0.3, 0.95) * (1 - y / ymax * 0.7)
        s += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{o:.2f}"/>'
    return s


def aurora(rnd, w, y0, bands=4):
    s = ""
    for i in range(bands):
        pts = []
        for j in range(9):
            pts.append((w * (j / 8) + rnd.uniform(-80, 80), y0 + rnd.uniform(-120, 120) + i * 40))
        d = f"M {pts[0][0]:.0f},{pts[0][1]:.0f} " + " ".join(
            f"S {(pts[k][0] + pts[k-1][0]) / 2:.0f},{pts[k][1] - 60:.0f} {pts[k][0]:.0f},{pts[k][1]:.0f}"
            for k in range(1, len(pts)))
        s += (f'<path d="{d}" fill="none" stroke="url(#aur)" stroke-width="{rnd.uniform(60, 140):.0f}" '
              f'opacity="{rnd.uniform(0.18, 0.35):.2f}" filter="url(#soft)" stroke-linecap="round"/>')
        # fine vertical curtain rays
        for _ in range(60):
            k = rnd.randrange(len(pts))
            x = pts[k][0] + rnd.uniform(-120, 120)
            yy = pts[k][1]
            s += (f'<line x1="{x:.0f}" y1="{yy - rnd.uniform(40, 220):.0f}" x2="{x:.0f}" '
                  f'y2="{yy + 30:.0f}" stroke="url(#aurv)" stroke-width="{rnd.uniform(3, 10):.0f}" '
                  f'opacity="{rnd.uniform(0.05, 0.18):.2f}" filter="url(#soft2)"/>')
    return s


def longship(x, y, s, hull="#06080d", sail_a=EMBER, sail_b=BONE, shields=(GOLD, FROST, OAK)):
    """An original longship silhouette; (x,y)=waterline centre, s=scale."""
    T = f'transform="translate({x},{y}) scale({s}) translate(-200,0)"'
    hullp = ("M -14,-78 C -10,-40 4,-8 30,4 Q 200,46 372,4 C 398,-6 414,-46 420,-96 "
             "C 422,-112 444,-116 446,-100 C 448,-88 432,-86 434,-98 C 428,-60 412,-18 386,-6 "
             "L 24,-6 C 8,-16 -4,-44 -6,-74 C -6,-90 -22,-92 -22,-80 C -22,-70 -12,-70 -14,-78 Z")
    g = f'<g {T}>'
    # mast & yard
    g += f'<rect x="196" y="-185" width="8" height="182" fill="{hull}"/>'
    g += f'<rect x="112" y="-170" width="176" height="7" rx="3" fill="{hull}"/>'
    # sail, billowed, striped
    sail = "M 118,-164 L 282,-164 C 290,-110 286,-70 276,-42 Q 200,-26 124,-42 C 114,-70 110,-110 118,-164 Z"
    g += f'<clipPath id="sailclip"><path d="{sail}"/></clipPath>'
    g += f'<g clip-path="url(#sailclip)">'
    for i in range(9):
        g += f'<rect x="{110 + i * 20}" y="-170" width="20" height="150" fill="{sail_a if i % 2 == 0 else sail_b}"/>'
    g += '<rect x="100" y="-170" width="200" height="150" fill="url(#sailshade)"/></g>'
    # rigging
    for (x1, y1, x2, y2) in ((200, -182, -6, -70), (200, -182, 420, -92), (112, -166, 60, -6), (288, -166, 340, -6)):
        g += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{hull}" stroke-width="2"/>'
    g += f'<path d="{hullp}" fill="{hull}"/>'
    # shields along the gunwale
    for i, sx in enumerate(range(48, 356, 26)):
        col = shields[i % len(shields)]
        g += f'<circle cx="{sx}" cy="-8" r="10" fill="{col}" opacity="0.85"/>'
        g += f'<circle cx="{sx}" cy="-8" r="3" fill="{hull}"/>'
    # oars
    for ox in range(70, 340, 34):
        g += f'<line x1="{ox}" y1="4" x2="{ox - 18}" y2="40" stroke="{hull}" stroke-width="3"/>'
    g += '</g>'
    return g


def wallpaper_fjord(w=3840, h=2160, seed=11, ship_x=0.36, ship_scale=2.6):
    rnd = random.Random(seed)
    hz = h * 0.62  # horizon / waterline
    defs = (
        '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#070b16"/><stop offset="0.45" stop-color="#1a2342"/>'
        f'<stop offset="0.80" stop-color="#5b3a4a"/><stop offset="1" stop-color="{EMBER}"/></linearGradient>'
        '<linearGradient id="water" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#3a2a3a"/><stop offset="0.25" stop-color="#151d33"/>'
        f'<stop offset="1" stop-color="#060912"/></linearGradient>'
        '<linearGradient id="aur" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#3fe0a0"/><stop offset="0.5" stop-color="#8fc4e0"/>'
        '<stop offset="1" stop-color="#9a7fe0"/></linearGradient>'
        '<linearGradient id="aurv" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9a7fe0" stop-opacity="0"/><stop offset="1" stop-color="#3fe0a0"/></linearGradient>'
        '<linearGradient id="sailshade" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#000" stop-opacity="0.55"/><stop offset="0.5" stop-color="#000" stop-opacity="0.25"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0.65"/></linearGradient>'
        '<radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0" stop-color="{GOLD_HI}" stop-opacity="0.9"/><stop offset="0.3" stop-color="{EMBER}" stop-opacity="0.45"/>'
        f'<stop offset="1" stop-color="{EMBER}" stop-opacity="0"/></radialGradient>'
        f'<filter id="soft" filterUnits="userSpaceOnUse" x="-800" y="-800" width="{w+1600}" height="{h+1600}"><feGaussianBlur stdDeviation="28"/></filter>'
        f'<filter id="soft2" filterUnits="userSpaceOnUse" x="-800" y="-800" width="{w+1600}" height="{h+1600}"><feGaussianBlur stdDeviation="6"/></filter>'
        '<filter id="blurref"><feGaussianBlur stdDeviation="3 10"/></filter>'
    )
    b = f'<rect width="{w}" height="{h}" fill="url(#sky)"/>'
    b += stars(rnd, w, h, 700, hz * 0.7)
    b += aurora(rnd, w, h * 0.22, 4)
    b += f'<ellipse cx="{w*0.62}" cy="{hz}" rx="{w*0.35}" ry="{h*0.22}" fill="url(#sun)"/>'
    # mountain layers: far → near, fjord walls on both sides
    layers = [("#3b2f45", 0.45, 110, 0.58), ("#272640", 0.22, 170, 0.56), ("#171a2c", 0.0, 220, 0.52)]
    land = ""
    for col, lift, amp, rough in layers:
        pts = ridge(rnd, w, hz - 300 - lift * 500, amp, rough)
        # carve a valley in the middle-right where the fjord opens
        pts = [(x, y + (420 + 300 * lift) * math.exp(-((x - w * 0.62) / (w * 0.13)) ** 2)) for x, y in pts]
        pts = [(x, min(y, hz)) for x, y in pts]
        land += poly(pts, w, hz, col)
    b += land
    # water + reflection of the land
    b += f'<rect y="{hz}" width="{w}" height="{h-hz}" fill="url(#water)"/>'
    b += (f'<g transform="translate(0,{2*hz}) scale(1,-1)" opacity="0.35" filter="url(#blurref)">{land}</g>')
    # sun glitter
    for _ in range(260):
        x = rnd.gauss(w * 0.62, w * 0.07)
        y = hz + abs(rnd.gauss(0, h * 0.09))
        ln = rnd.uniform(20, 120)
        b += f'<rect x="{x:.0f}" y="{y:.0f}" width="{ln:.0f}" height="3" fill="{GOLD_HI}" opacity="{rnd.uniform(0.15, 0.6):.2f}"/>'
    # the ship + its reflection
    sx, sc = w * ship_x, ship_scale
    b += longship(sx, hz + 6, sc)
    b += (f'<g transform="translate(0,{2*(hz+6)}) scale(1,-1)" opacity="0.30" filter="url(#blurref)">'
          f'{longship(sx, hz + 6, sc)}</g>')
    # ripples
    for _ in range(140):
        x = rnd.uniform(0, w)
        y = hz + rnd.uniform(10, h - hz) ** 1.0
        b += (f'<rect x="{x:.0f}" y="{y:.0f}" width="{rnd.uniform(40, 260):.0f}" height="2" '
              f'fill="{FROST}" opacity="{rnd.uniform(0.04, 0.12):.2f}"/>')
    return svg(w, h, b, defs)


def fjord_layers(w=1440, h=3120, seed=11, ship_x=0.40, ship_scale=1.85):
    """The phone fjord split for the living wallpaper: 'land' (mountains only) and
    'ship' (longship, its reflection, ripples), both on transparent ground. Uses the
    same random sequence as wallpaper_fjord, so the mountains match it exactly."""
    rnd = random.Random(seed)
    hz = h * 0.62
    stars(rnd, w, h, 700, hz * 0.7)          # consumed only to keep the sequence identical
    aurora(rnd, w, h * 0.22, 4)
    layers = [("#3b2f45", 0.45, 110, 0.58), ("#272640", 0.22, 170, 0.56), ("#171a2c", 0.0, 220, 0.52)]
    land = ""
    for col, lift, amp, rough in layers:
        pts = ridge(rnd, w, hz - 300 - lift * 500, amp, rough)
        pts = [(x, y + (420 + 300 * lift) * math.exp(-((x - w * 0.62) / (w * 0.13)) ** 2)) for x, y in pts]
        pts = [(x, min(y, hz)) for x, y in pts]
        land += poly(pts, w, hz, col)
    for _ in range(260):                      # sun glitter in the original: drawn live instead
        rnd.gauss(w * 0.62, w * 0.07); abs(rnd.gauss(0, h * 0.09)); rnd.uniform(20, 120); rnd.uniform(0.15, 0.6)
    defs = ('<linearGradient id="sailshade" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#000" stop-opacity="0.55"/><stop offset="0.5" stop-color="#000" stop-opacity="0.25"/>'
            '<stop offset="1" stop-color="#000" stop-opacity="0.65"/></linearGradient>'
            '<filter id="blurref"><feGaussianBlur stdDeviation="3 10"/></filter>')
    sx, sc = w * ship_x, ship_scale
    ship = longship(sx, hz + 6, sc)
    ship += (f'<g transform="translate(0,{2*(hz+6)}) scale(1,-1)" opacity="0.30" filter="url(#blurref)">'
             f'{longship(sx, hz + 6, sc)}</g>')
    for _ in range(140):
        x = rnd.uniform(0, w)
        y = hz + rnd.uniform(10, h - hz) ** 1.0
        ship += (f'<rect x="{x:.0f}" y="{y:.0f}" width="{rnd.uniform(40, 260):.0f}" height="2" '
                 f'fill="{FROST}" opacity="{rnd.uniform(0.04, 0.12):.2f}"/>')
    return {"land": svg(w, h, land), "ship": svg(w, h, ship, defs)}


def wallpaper_worldtree(w=3840, h=2160, seed=5, tree_scale=3.0, ring_scale=1.0):
    rnd = random.Random(seed)
    defs = (
        '<radialGradient id="bg" cx="0.5" cy="0.45" r="0.75">'
        f'<stop offset="0" stop-color="#1c2a44"/><stop offset="0.55" stop-color="{NIGHT2}"/>'
        f'<stop offset="1" stop-color="#05080f"/></radialGradient>'
        '<radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0" stop-color="{GOLD}" stop-opacity="0.35"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>'
        + GLOW.format(s=6) +
        '<filter id="soft"><feGaussianBlur stdDeviation="40"/></filter>'
    )
    b = f'<rect width="{w}" height="{h}" fill="url(#bg)"/>'
    b += stars(rnd, w, h, 900, h)
    # three faint realm rings
    for r, o in ((900, 0.10), (680, 0.08), (460, 0.06)):
        r = r * ring_scale
        b += f'<circle cx="{w/2}" cy="{h*0.5}" r="{r}" fill="none" stroke="{FROST}" stroke-width="2" opacity="{o}"/>'
    b += f'<ellipse cx="{w/2}" cy="{h*0.45}" rx="900" ry="700" fill="url(#halo)"/>'
    b += tree_group(w / 2, h * 0.54, tree_scale, GOLD, seed=7, glow=True, crown_depth=8, root_depth=6)
    # rune band along the bottom
    d, tw = rune_text(BAND_RUNES, 0, 0, 46, gap=0.9)
    b += (f'<path d="{d}" transform="translate({(w - tw) / 2},{h - 140})" fill="none" '
          f'stroke="{GOLD}" stroke-width="4" stroke-linecap="round" opacity="0.55"/>')
    return svg(w, h, b, defs)


def wallpaper_iron(w=3840, h=2160, seed=2):
    """Quiet, low-distraction work wallpaper: dark iron with a faint knot lattice."""
    rnd = random.Random(seed)
    defs = (
        '<radialGradient id="bg" cx="0.3" cy="0.3" r="1">'
        f'<stop offset="0" stop-color="#232a35"/><stop offset="1" stop-color="#0c1018"/></radialGradient>'
        '<pattern id="knot" width="160" height="160" patternUnits="userSpaceOnUse">'
        f'<path d="M0,80 C40,0 120,0 160,80 M0,80 C40,160 120,160 160,80 M80,0 C0,40 0,120 80,160 M80,0 C160,40 160,120 80,160" '
        f'fill="none" stroke="{GOLD}" stroke-width="3" opacity="0.06"/></pattern>'
    )
    b = f'<rect width="{w}" height="{h}" fill="url(#bg)"/>'
    b += f'<rect width="{w}" height="{h}" fill="url(#knot)"/>'
    # small logo bottom-right, very subtle
    portrait = h > w
    size = 760 if portrait else 520
    lg = logo(size, color=GOLD, band=True)
    inner = lg[lg.index('</defs>') + 7:lg.rindex('</svg>')]
    x, y = ((w - size) / 2, h * 0.58 - size / 2) if portrait else (w - 760, h - 760)
    b += f'<g transform="translate({x},{y})" opacity="{0.22 if portrait else 0.18}">{inner}</g>'
    return svg(w, h, b, defs)


def login_bg(w=3840, h=2160):
    return wallpaper_fjord(w, h, seed=11)


def splash_runes(out):
    """Individual rune PNG sources for Plymouth / ksplash animation."""
    for i, k in enumerate(NAME_RUNES):
        hh = 120
        d, wd = rune_path(k, 20, 20, hh)
        W = int(wd + 40)
        body = (f'<path d="{d}" fill="none" stroke="{GOLD_HI}" stroke-width="9" '
                f'stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>')
        flt = GLOW.format(s=4).replace('x="-20%" y="-20%" width="140%" height="140%"',
                                       f'filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{hh + 40}"')
        open(os.path.join(out, f"rune{i}.svg"), "w").write(svg(W, hh + 40, body, flt))


def name_runes_svg(h=120, color=GOLD):
    d, tw = rune_text(NAME_RUNES, 20, 20, h, gap=0.45)
    body = (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{h*0.07:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    return svg(int(tw + 40), h + 40, body)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "art-out"
    os.makedirs(out, exist_ok=True)
    files = {
        "logo.svg": logo(512),
        "logo-dark.svg": logo(512, bg=NIGHT),
        "logo-symbolic.svg": logo_symbolic(64),
        "wall-fjord.svg": wallpaper_fjord(),
        "wall-worldtree.svg": wallpaper_worldtree(),
        "wall-iron.svg": wallpaper_iron(),
        "name-runes.svg": name_runes_svg(),
        # phone (portrait) versions for the Android launcher
        "phone-fjord.svg": wallpaper_fjord(1440, 3120, seed=11, ship_x=0.40, ship_scale=1.85),
        "phone-worldtree.svg": wallpaper_worldtree(1440, 3120, seed=5, tree_scale=1.45, ring_scale=0.75),
        "phone-iron.svg": wallpaper_iron(1440, 3120),
    }
    for n, s in files.items():
        open(os.path.join(out, n), "w").write(s)
    splash_runes(out)
    os.makedirs(os.path.join(out, "icons"), exist_ok=True)
    for name, data in power_icons().items():
        open(os.path.join(out, "icons", f"{name}.svg"), "w").write(data)
    print("wrote", len(files) + len(NAME_RUNES), "svgs to", out)


if __name__ == "__main__":
    main()
