#!/usr/bin/env python3
"""Yggdrasil cursor scheme for Windows: carved gold with a frost edge.

    python3 windows/tools/win_cursors.py OUT_DIR

Writes one multi-size .cur (or animated .ani) per Windows pointer role. Each file
holds 32, 48, 64, 96 and 128 px images (32-bit with alpha), so the cursors stay sharp
at any pointer size and display scale. Needs rsvg-convert and Pillow.
"""
import io
import math
import os
import struct
import subprocess
import sys
import tempfile

from PIL import Image

GOLD, GOLD_HI, FROST, NIGHT, BONE, EMBER, CARVE = "#c8a25a", "#ecd08f", "#8fc4e0", "#0b1220", "#e8dcc4", "#e0703a", "#5a4420"
SIZES = (32, 48, 64, 96, 128)
ANI_SIZES = (32, 48, 64, 128)   # what Windows' .ani loader accepted on allfather (no 96)
FRAMES = 24          # busy ring: 15 degrees a frame
RATE = 3             # jiffies (1/60 s) per frame -> 20 fps


# ------------------------------------------------------------------ drawing (32-unit grid)
def svg(body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{GOLD_HI}"/><stop offset="0.55" stop-color="{GOLD}"/>'
            f'<stop offset="1" stop-color="#a8843f"/></linearGradient>{defs}</defs>{body}</svg>')


def carved(d, fill="url(#g)", inner=True):
    """A shape with a frost outer edge, a night rim and a carved inner line."""
    s = (f'<path d="{d}" fill="none" stroke="{FROST}" stroke-width="2.6" stroke-linejoin="round" opacity="0.9"/>'
         f'<path d="{d}" fill="{fill}" stroke="{NIGHT}" stroke-width="1.2" stroke-linejoin="round"/>')
    if inner:
        s += f'<path d="{d}" fill="none" stroke="{CARVE}" stroke-width="0.5" stroke-linejoin="round" transform="translate(0.9 0.9) scale(0.94)" opacity="0.55"/>'
    return s


ARROW = "M1.5,1.5 L1.5,22 L6.6,17.2 L10.2,25.4 L13.6,23.9 L10.1,15.9 L17,15.9 Z"


def arrow():
    # the classic arrow, with two rune notches carved across its tail
    return carved(ARROW) + f'<path d="M3.2,8.5 L6.4,11.2 M3.2,12.6 L5.6,14.6" stroke="{CARVE}" stroke-width="0.8"/>'


def ring(cx, cy, r, phase, w=2.2):
    """Gold ring with rune notches; a bright arc sweeps round as the frames advance."""
    a0 = phase
    a1 = phase + 110
    p = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = p(a0), p(a1)
    notches = "".join(
        f'<path d="M{cx + (r - w) * math.cos(math.radians(a)):.2f},{cy + (r - w) * math.sin(math.radians(a)):.2f} '
        f'L{cx + (r + w) * math.cos(math.radians(a)):.2f},{cy + (r + w) * math.sin(math.radians(a)):.2f}" '
        f'stroke="{NIGHT}" stroke-width="0.8"/>' for a in range(0, 360, 45))
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{FROST}" stroke-width="{w + 2.2}" opacity="0.85"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{NIGHT}" stroke-width="{w + 1}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GOLD}" stroke-width="{w}"/>'
            f'<path d="M{x0:.2f},{y0:.2f} A{r},{r} 0 0 1 {x1:.2f},{y1:.2f}" fill="none" stroke="{GOLD_HI}" stroke-width="{w}" stroke-linecap="round"/>'
            + notches)


def double_arrow(angle):
    d = "M16,2.5 L21.5,8.5 L18,8.5 L18,23.5 L21.5,23.5 L16,29.5 L10.5,23.5 L14,23.5 L14,8.5 L10.5,8.5 Z"
    notch = f'<path d="M14.6,14 L17.4,14 M14.6,18 L17.4,18" stroke="{CARVE}" stroke-width="0.8"/>'
    return f'<g transform="rotate({angle} 16 16)">{carved(d)}{notch}</g>'


def badge(body):
    """Arrow plus a small emblem at its lower right (help, pin, person, working)."""
    return arrow() + body


def cursors():
    """role -> (frames: [svg], hotspot (x, y) on the 32 grid)"""
    c = {}
    c["Arrow"] = ([svg(arrow())], (1.5, 1.5))
    c["Help"] = ([svg(badge(
        f'<circle cx="23.5" cy="23.5" r="7" fill="{FROST}" stroke="{NIGHT}" stroke-width="1.2"/>'
        f'<path d="M20.8,21.2 Q20.8,18.4 23.5,18.4 Q26.2,18.4 26.2,21 Q26.2,22.6 23.5,23.6 L23.5,25.2" fill="none" stroke="{NIGHT}" stroke-width="1.7"/>'
        f'<circle cx="23.5" cy="27.6" r="1.05" fill="{NIGHT}"/>'))], (1.5, 1.5))
    c["AppStarting"] = ([svg(badge(ring(24, 24, 5.2, f * 15, 1.8))) for f in range(FRAMES)], (1.5, 1.5))
    c["Wait"] = ([svg(ring(16, 16, 10.5, f * 15, 3)) for f in range(FRAMES)], (16, 16))
    c["Crosshair"] = ([svg(
        f'<path d="M16,2 L16,12 M16,20 L16,30 M2,16 L12,16 M20,16 L30,16" stroke="{NIGHT}" stroke-width="3.4"/>'
        f'<path d="M16,2 L16,12 M16,20 L16,30 M2,16 L12,16 M20,16 L30,16" stroke="{FROST}" stroke-width="1.6"/>'
        f'<circle cx="16" cy="16" r="2.2" fill="{GOLD}" stroke="{NIGHT}" stroke-width="1"/>')], (16, 16))
    beam = "M11,3 L21,3 L21,5.5 L17.4,5.5 L17.4,26.5 L21,26.5 L21,29 L11,29 L11,26.5 L14.6,26.5 L14.6,5.5 L11,5.5 Z"
    c["IBeam"] = ([svg(carved(beam, fill=BONE, inner=False))], (16, 16))
    chisel = "M3,29 L5.5,22.5 L22.5,5.5 L26.5,9.5 L9.5,26.5 Z"
    c["NWPen"] = ([svg(carved(chisel) + f'<path d="M3,29 L5.5,22.5 L9.5,26.5 Z" fill="{FROST}" stroke="{NIGHT}" stroke-width="0.8"/>')], (3, 29))
    c["No"] = ([svg(
        f'<circle cx="16" cy="16" r="11.5" fill="none" stroke="{NIGHT}" stroke-width="5.4"/>'
        f'<circle cx="16" cy="16" r="11.5" fill="none" stroke="{EMBER}" stroke-width="3.4"/>'
        f'<path d="M8,8 L24,24" stroke="{NIGHT}" stroke-width="5.4"/><path d="M8,8 L24,24" stroke="{EMBER}" stroke-width="3.4"/>')], (16, 16))
    c["SizeNS"] = ([svg(double_arrow(0))], (16, 16))
    c["SizeWE"] = ([svg(double_arrow(90))], (16, 16))
    c["SizeNWSE"] = ([svg(double_arrow(-45))], (16, 16))
    c["SizeNESW"] = ([svg(double_arrow(45))], (16, 16))
    move = ("M16,1.5 L21,6.5 L17.6,6.5 L17.6,14.4 L25.5,14.4 L25.5,11 L30.5,16 L25.5,21 L25.5,17.6 L17.6,17.6 "
            "L17.6,25.5 L21,25.5 L16,30.5 L11,25.5 L14.4,25.5 L14.4,17.6 L6.5,17.6 L6.5,21 L1.5,16 L6.5,11 "
            "L6.5,14.4 L14.4,14.4 L14.4,6.5 L11,6.5 Z")
    c["SizeAll"] = ([svg(carved(move))], (16, 16))
    up = "M16,1.5 L25,11.5 L19,11.5 L19,30 L13,30 L13,11.5 L7,11.5 Z"
    c["UpArrow"] = ([svg(carved(up) + f'<path d="M14,18 L18,18 M14,23 L18,23" stroke="{CARVE}" stroke-width="0.8"/>')], (16, 1.5))
    # Link select: a spear, tip at the hotspot
    spear = "M1.5,1.5 L12.5,4.5 L9.6,7.4 L29.5,27.3 L27.3,29.5 L7.4,9.6 L4.5,12.5 Z"
    c["Hand"] = ([svg(carved(spear) + f'<path d="M10.2,12.6 L12.6,10.2 M13.2,15.6 L15.6,13.2" stroke="{NIGHT}" stroke-width="1.4"/>')], (1.5, 1.5))
    c["Pin"] = ([svg(badge(
        f'<path d="M24,31 L19.2,23.4 A5.6,5.6 0 1 1 28.8,23.4 Z" fill="{EMBER}" stroke="{NIGHT}" stroke-width="1.2"/>'
        f'<circle cx="24" cy="20.4" r="2" fill="{NIGHT}"/>'))], (1.5, 1.5))
    c["Person"] = ([svg(badge(
        f'<circle cx="24" cy="19.5" r="3.4" fill="{BONE}" stroke="{NIGHT}" stroke-width="1.1"/>'
        f'<path d="M17.5,30.5 Q17.5,24 24,24 Q30.5,24 30.5,30.5 Z" fill="{BONE}" stroke="{NIGHT}" stroke-width="1.1"/>'))], (1.5, 1.5))
    return c


# ------------------------------------------------------------------ file formats
def render(svg_text, size, tmp):
    src = os.path.join(tmp, "c.svg")
    dst = os.path.join(tmp, f"c{size}.png")
    with open(src, "w") as f:
        f.write(svg_text)
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), src, "-o", dst], check=True)
    return Image.open(dst).convert("RGBA")


def dib(img):
    """32-bit BGRA DIB with AND mask, as stored inside .cur/.ico."""
    w, h = img.size
    hdr = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    px = img.transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "BGRA")
    row = ((w + 31) // 32) * 4
    mask = bytearray()
    flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
    a = flipped.getchannel("A").tobytes()
    for y in range(h):
        bits = bytearray(row)
        for x in range(w):
            if a[y * w + x] == 0:
                bits[x // 8] |= 0x80 >> (x % 8)
        mask += bits
    return hdr + px + bytes(mask)


def cur(images, hot):
    """images: [(size, PIL image)] -> .cur bytes with per-size hotspots."""
    head = struct.pack("<HHH", 0, 2, len(images))
    entries, blobs = b"", b""
    offset = 6 + 16 * len(images)
    for size, img in images:
        data = dib(img)
        hx = min(size - 1, round(hot[0] * size / 32))
        hy = min(size - 1, round(hot[1] * size / 32))
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, hx, hy, len(data), offset)
        blobs += data
        offset += len(data)
    return head + entries + blobs


def ani(frames, rate):
    """frames: [cur bytes] -> RIFF ACON animated cursor."""
    def chunk(tag, data):
        pad = b"\0" if len(data) % 2 else b""
        return tag + struct.pack("<I", len(data)) + data + pad
    # Plain layout, no INFO list: Windows rejected the earlier version as corrupt.
    anih = struct.pack("<9I", 36, len(frames), len(frames), 0, 0, 0, 0, rate, 1)  # AF_ICON
    fram = chunk(b"LIST", b"fram" + b"".join(chunk(b"icon", f) for f in frames))
    body = b"ACON" + chunk(b"anih", anih) + fram
    return b"RIFF" + struct.pack("<I", len(body)) + body


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "win-cursors"
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for role, (frames, hot) in cursors().items():
            sizes = SIZES if len(frames) == 1 else ANI_SIZES
            curs = [cur([(s, render(f, s, tmp)) for s in sizes], hot) for f in frames]
            if len(curs) == 1:
                name, data = f"Yggdrasil {role}.cur", curs[0]
            else:
                name, data = f"Yggdrasil {role}.ani", ani(curs, RATE)
            with open(os.path.join(out, name), "wb") as f:
                f.write(data)
            print(name, len(data))
        # preview sheet for review (not shipped)
        if os.environ.get("PREVIEW"):
            sheet = Image.new("RGBA", (17 * 72, 2 * 72), (240, 240, 240, 255))
            dark = Image.new("RGBA", (17 * 72, 72), (11, 18, 32, 255)); sheet.paste(dark, (0, 72))
            for i, (role, (frames, _)) in enumerate(cursors().items()):
                im = render(frames[0], 64, tmp)
                sheet.alpha_composite(im, (i * 72 + 4, 4)); sheet.alpha_composite(im, (i * 72 + 4, 76))
            sheet.save(os.environ["PREVIEW"])


if __name__ == "__main__":
    main()
