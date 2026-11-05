#!/usr/bin/env python3
"""Yggdrasil shield icons for Windows: desktop icons (This PC, user folder, network,
Recycle Bin) and folder emblems, as round longship shields with a carved glyph,
the same style as Yggdrasil OS's login buttons and the launcher's app shields.

    python3 windows/tools/win_icons.py OUT_DIR
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import art  # noqa: E402
from art import BONE, EMBER, FROST, GOLD, shield_icon  # noqa: E402

OAK = "#a67c4e"   # the launcher's oak shield
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def rune(key, h=30):
    d, w = art.rune_path(key, 32 - (art.RUNES[key][0] * h) / 2, 32 - h / 2, h)
    return f'<path d="{d}"/>'


def solid(d):
    return f'<path d="{d}" fill="#141a26" stroke="none"/>'


GLYPHS = {
    # desktop
    "This PC": (GOLD, '<path d="M17,19 L47,19 L47,39 L17,39 Z"/><path d="M32,39 L32,46 M23,47 L41,47"/>'),
    "User": (BONE, '<path d="M32,17 L38,23 L32,29 L26,23 Z"/><path d="M19,47 L23,35 L41,35 L45,47"/>'),
    "Network": (FROST, '<path d="M32,18 L32,30 M32,30 L20,44 M32,30 L44,44 M20,44 L44,44"/>'
                       '<path d="M29,15 L35,15 L35,21 L29,21 Z M17,41 L23,41 L23,47 L17,47 Z M41,41 L47,41 L47,47 L41,47 Z" fill="#141a26"/>'),
    "Recycle Bin Empty": (OAK, '<path d="M19,22 L45,22 M23,22 L25,47 L39,47 L41,22 M29,22 L29,17 L35,17 L35,22"/>'),
    "Recycle Bin Full": (OAK, '<path d="M19,22 L45,22 M23,22 L25,47 L39,47 L41,22 M29,22 L29,17 L35,17 L35,22"/>'
                              + solid("M27,29 L31,27 L33,31 L29,33 Z M33,35 L37,33 L38,38 L34,39 Z M28,38 L31,36 L32,41 L28,42 Z")),
    # folders
    "Folder": (GOLD, rune("P")),                               # perth: the dice cup, a container
    "Documents": (BONE, rune("A")),                            # ansuz: words
    "Downloads": (FROST, '<path d="M32,16 L32,38 M23,30 L32,39 L41,30 M19,47 L45,47"/>'),
    "Pictures": (GOLD, '<path d="M16,45 L27,28 L34,38 L39,32 L48,45 Z"/><path d="M41,18 L46,18 L46,23 L41,23 Z" fill="#141a26"/>'),
    "Music": (GOLD, '<path d="M32,47 Q17,41 21,17 M32,47 Q47,41 43,17 M20,21 L44,21"/>'
                    '<path d="M27,24 L28,41 M32,24 L32,44 M37,24 L36,41" stroke-width="2.4"/>'),     # lyre
    "Videos": (EMBER, '<path d="M24,18 L44,32 L24,46 Z"/>'),
    "Games": (EMBER, '<path d="M20,48 L40,20"/>' + solid("M33,15 Q49,15 48,33 L36,25 Z")),   # an axe
    "Code": (FROST, '<path d="M26,20 L16,32 L26,44 M38,20 L48,32 L38,44"/>'),
    "Projects": (OAK, '<path d="M19,19 L45,19 L45,29 L19,29 Z M32,29 L32,47"/>'),       # Mjolnir
    "Archive": (OAK, rune("E")),                               # ehwaz
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "win-icons"
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, (fill, glyph) in GLYPHS.items():
            src = os.path.join(tmp, "i.svg")
            with open(src, "w") as f:
                f.write(shield_icon(fill, glyph, 64))
            imgs = []
            for s in SIZES:
                png = os.path.join(tmp, f"{s}.png")
                subprocess.run(["rsvg-convert", "-w", str(s), "-h", str(s), src, "-o", png], check=True)
                imgs.append(Image.open(png).convert("RGBA"))
            dst = os.path.join(out, f"{name}.ico")
            imgs[-1].save(dst, sizes=[(s, s) for s in SIZES], append_images=imgs[:-1])
            print(os.path.basename(dst))
        if os.environ.get("PREVIEW"):
            sheet = Image.new("RGBA", (len(GLYPHS) * 104, 104), (11, 18, 32, 255))
            for i, name in enumerate(GLYPHS):
                sheet.alpha_composite(Image.open(os.path.join(out, f"{name}.ico")).resize((96, 96)), (i * 104 + 4, 4))
            sheet.save(os.environ["PREVIEW"])


if __name__ == "__main__":
    main()
