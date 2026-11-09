#!/usr/bin/env python3
"""Yggdrasil Windows artwork: 32:9 wallpapers for the Odyssey G9, the lock
screen, and the land / ship layers the living wallpaper (Yggdrasil Sky) paints
its sky behind.

    python3 windows/tools/win_art.py OUT_DIR [WIDTH HEIGHT]

Writes SVGs; windows/tools/build.sh renders them to PNG/JPG.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import art  # noqa: E402

# Yggdrasil rule: never sowilo, tiwaz, algiz, othala or jera.
FORBIDDEN = {"S", "Y", "T", "Z", "O"}
art.BAND_RUNES = [k for k in art.BAND_RUNES if k not in FORBIDDEN]
art.NAME_RUNES = [k for k in art.NAME_RUNES if k not in FORBIDDEN]


def check_scene(w, h, ship_x, ship_scale):
    """The living scene places the reflection and oars from these same numbers: stop if they differ."""
    js = open(os.path.join(os.path.dirname(__file__), "..", "sky", "web", "scene.js")).read()
    m = re.search(r"const SHIP = \{ x: ([\d.]+), wl: ([\d.]+), s: ([\d.]+), draft: (\d+) \};", js)
    if not m:
        sys.exit("scene.js: no SHIP line")
    want = (w * ship_x, h * 0.62, ship_scale, art.SHIP_DRAFT)
    got = tuple(float(g) for g in m.groups())
    if any(abs(a - b) > 1e-3 for a, b in zip(want, got)):
        sys.exit(f"scene.js SHIP {got} doesn't match the art {want}: update the SHIP line")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "win-art"
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 5120
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
    os.makedirs(out, exist_ok=True)
    k = h / 2160  # the desktop art was tuned at 2160 tall
    ship_x, ship_scale = 0.40, 2.6 * k * 1.15
    files = {
        "wall-fjord.svg": art.wallpaper_fjord(w, h, seed=11, ship_x=ship_x, ship_scale=ship_scale, afloat=True),
        "wall-worldtree.svg": art.wallpaper_worldtree(w, h, seed=5, tree_scale=2.7 * k, ring_scale=k),
        "wall-iron.svg": art.wallpaper_iron(w, h),
        "logo.svg": art.logo(512),
    }
    layers = art.fjord_layers(w, h, seed=11, ship_x=ship_x, ship_scale=ship_scale, afloat=True, live=True)
    check_scene(w, h, ship_x, ship_scale)
    files["sky-land.svg"] = layers["land"]
    files["sky-ship.svg"] = layers["ship"]
    for n, s in files.items():
        with open(os.path.join(out, n), "w") as f:
            f.write(s)
    print("wrote", len(files), "svgs to", out)


if __name__ == "__main__":
    main()
