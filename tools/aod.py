#!/usr/bin/env python3
"""Always On Display image for the phone: the world-tree rune ring as thin,
dim gold lines on black. Few lit pixels = little battery.

    python3 tools/aod.py OUT.png
"""
import subprocess
import sys

import art

# the phone's rune set: no sowilo, tiwaz, algiz or othala; no jera (reads as sowilo when small)
art.BAND_RUNES = [k for k in art.BAND_RUNES if k not in ("S", "Y")]
AOD_GOLD = "#b08f50"


def main(out):
    size = 1080
    body = art.logo(size, color=AOD_GOLD, bg=None, band=True)
    body = body.replace("<defs>", '<defs></defs><rect width="100%" height="100%" fill="#000"/><defs>', 1)
    svg_path = out.rsplit(".", 1)[0] + ".svg"
    with open(svg_path, "w") as f:
        f.write(body)
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", out, svg_path], check=True)


def lock(out, w=1440, h=3120):
    """Full-height lock screen / AOD wallpaper: the ring on black, below the lock clock."""
    size = int(w * 0.86)
    ring = art.logo(size, color=AOD_GOLD, bg=None, band=True)
    inner = ring.split(">", 1)[1].rsplit("</svg>", 1)[0]       # drop the outer <svg ...> wrapper
    x, y = (w - size) / 2, h * 0.52 - size / 2
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect width="{w}" height="{h}" fill="#000"/><g transform="translate({x:.1f},{y:.1f})">{inner}</g></svg>')
    svg_path = out.rsplit(".", 1)[0] + ".svg"
    with open(svg_path, "w") as f:
        f.write(body)
    subprocess.run(["rsvg-convert", "-w", str(w), "-h", str(h), "-o", out, svg_path], check=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "aod.png")
    if len(sys.argv) > 2:
        lock(sys.argv[2])
