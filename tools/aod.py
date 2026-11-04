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


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "aod.png")
