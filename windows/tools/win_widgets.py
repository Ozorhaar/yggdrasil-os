#!/usr/bin/env python3
"""Carved frames and bar notches for the Yggdrasil Rainmeter skins.

    python3 windows/tools/win_widgets.py RESOURCES_DIR
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import art  # noqa: E402
from art import GOLD, GOLD_HI, NIGHT, NIGHT2  # noqa: E402

assert not set(art.BAND_RUNES) & set(art.AVOID)


def frame(w, h, band=True):
    r = 14
    runes = ""
    if band:
        keys = (art.BAND_RUNES * 3)[: max(1, int((w - 80) / 30))]
        d, tw = art.rune_text(keys, 0, 0, 16, gap=0.9)
        runes = (f'<g transform="translate({(w - tw) / 2:.1f} {h - 34})" fill="none" stroke="{GOLD}" '
                 f'stroke-opacity="0.55" stroke-width="2" stroke-linecap="square"><path d="{d}"/></g>'
                 f'<path d="M24,{h - 44} L{w - 24},{h - 44}" stroke="{GOLD}" stroke-opacity="0.35" stroke-width="1.5"/>')
    rivets = "".join(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{GOLD}" stroke="{NIGHT}" stroke-width="1"/>'
                     for x, y in ((14, 14), (w - 14, 14), (14, h - 14), (w - 14, h - 14)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
            f'<defs><linearGradient id="p" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{NIGHT2}"/><stop offset="1" stop-color="{NIGHT}"/></linearGradient>'
            f'<linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD_HI}"/>'
            f'<stop offset="0.5" stop-color="{GOLD}"/><stop offset="1" stop-color="#8a6b30"/></linearGradient></defs>'
            f'<rect x="3" y="3" width="{w - 6}" height="{h - 6}" rx="{r}" fill="url(#p)" fill-opacity="0.88" '
            f'stroke="url(#rim)" stroke-width="3"/>'
            f'<rect x="9" y="9" width="{w - 18}" height="{h - 18}" rx="{r - 5}" fill="none" stroke="#000" '
            f'stroke-opacity="0.35" stroke-width="1.5"/>{rivets}{runes}</svg>')


def notches(w, h):
    """Carved tick marks laid over the meter bars (every 10%)."""
    ticks = "".join(f'<path d="M{w * i / 10:.1f},0 L{w * i / 10:.1f},{h}" stroke="{NIGHT}" stroke-opacity="0.55" stroke-width="2"/>'
                    for i in range(1, 10))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{ticks}'
            f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" fill="none" stroke="{GOLD}" stroke-opacity="0.6" stroke-width="1.5"/></svg>')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "widgets"
    os.makedirs(out, exist_ok=True)
    files = {"frame-clock": frame(560, 232), "frame-meters": frame(560, 330, band=False), "notches": notches(340, 16)}
    with tempfile.TemporaryDirectory() as tmp:
        for name, s in files.items():
            src = os.path.join(tmp, name + ".svg")
            with open(src, "w") as f:
                f.write(s)
            subprocess.run(["rsvg-convert", src, "-o", os.path.join(out, name + ".png")], check=True)
            print(name + ".png")


if __name__ == "__main__":
    main()
