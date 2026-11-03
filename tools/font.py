#!/usr/bin/env python3
"""Builds "Yggdrasil Runic" — a Latin display font drawn like carved runes.

Design rule: runes were cut across the wood grain, so there are no horizontal
strokes. Every crossbar and arm is slanted. Capitals are full height; lower
case is a small-caps set of the same shapes. The real Elder Futhark runes are
included at their Unicode code points, matching the boot-splash runes.

    python3 tools/font.py out/YggdrasilRunic.ttf
"""
import os
import sys

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(__file__))
from art import RUNES  # noqa: E402  (rune shapes shared with the artwork)

UPM = 1000
CAP = 700
SW = 78            # stroke weight
SC = 0.72          # small-caps height ratio
SIDE = 55          # side bearing
SCALE = CAP - SW   # design units (0..1 tall) → font units

# --------------------------------------------------------------- Latin, y-up, 0..1 tall
# Each entry: (width, [polyline, ...]); a polyline whose first and last
# points match is drawn closed.
L = {
    "A": (.62, [[(0, 0), (.31, 1), (.62, 0)], [(.12, .28), (.50, .42)]]),
    "B": (.50, [[(0, 0), (0, 1)], [(0, 1), (.46, .79), (0, .52), (.48, .25), (0, 0)]]),
    "C": (.48, [[(.48, .92), (.24, 1), (0, .72), (0, .28), (.24, 0), (.48, .08)]]),
    "D": (.54, [[(0, 0), (0, 1), (.54, .74), (.54, .26), (0, 0)]]),
    "E": (.46, [[(0, 0), (0, 1)], [(0, 1), (.46, .86)], [(0, .56), (.38, .42)], [(0, 0), (.46, .14)]]),
    "F": (.46, [[(0, 0), (0, 1)], [(0, 1), (.46, .86)], [(0, .56), (.38, .42)]]),
    "G": (.56, [[(.56, .86), (.28, 1), (0, .72), (0, .28), (.28, 0), (.56, .16), (.56, .46), (.28, .38)]]),
    "H": (.56, [[(0, 0), (0, 1)], [(.56, 0), (.56, 1)], [(0, .60), (.56, .40)]]),
    "I": (0, [[(0, 0), (0, 1)]]),
    "J": (.42, [[(.42, 1), (.42, .2), (.2, 0), (0, .16)]]),
    "K": (.50, [[(0, 0), (0, 1)], [(.50, 1), (0, .45)], [(.14, .58), (.50, 0)]]),
    "L": (.44, [[(0, 1), (0, 0), (.44, .14)]]),
    "M": (.72, [[(0, 0), (0, 1), (.36, .52), (.72, 1), (.72, 0)]]),
    "N": (.56, [[(0, 0), (0, 1), (.56, 0), (.56, 1)]]),
    "O": (.56, [[(.28, 1), (.56, .74), (.56, .26), (.28, 0), (0, .26), (0, .74), (.28, 1)]]),
    "P": (.48, [[(0, 0), (0, 1), (.48, .79), (0, .50)]]),
    "Q": (.62, [[(.28, 1), (.56, .74), (.56, .26), (.28, 0), (0, .26), (0, .74), (.28, 1)],
                [(.32, .24), (.62, -.10)]]),
    "R": (.52, [[(0, 0), (0, 1), (.48, .79), (0, .52), (.52, 0)]]),
    "S": (.48, [[(.48, .88), (.24, 1), (0, .76), (.48, .24), (.24, 0), (0, .12)]]),
    "T": (.58, [[(.29, 0), (.29, .98)], [(0, .90), (.58, 1.0)]]),
    "U": (.56, [[(0, 1), (0, .22), (.28, 0), (.56, .22), (.56, 1)]]),
    "V": (.62, [[(0, 1), (.31, 0), (.62, 1)]]),
    "W": (.86, [[(0, 1), (.21, 0), (.43, .66), (.65, 0), (.86, 1)]]),
    "X": (.58, [[(0, 0), (.58, 1)], [(0, 1), (.58, 0)]]),
    "Y": (.60, [[(0, 1), (.30, .52), (.60, 1)], [(.30, .52), (.30, 0)]]),
    "Z": (.56, [[(0, .90), (.56, 1), (0, 0), (.56, .10)]]),
    # digits
    "0": (.50, [[(.25, 1), (.5, .76), (.5, .24), (.25, 0), (0, .24), (0, .76), (.25, 1)], [(.08, .3), (.42, .7)]]),
    "1": (.30, [[(0, .78), (.30, 1), (.30, 0)]]),
    "2": (.50, [[(0, .80), (.25, 1), (.5, .80), (.5, .60), (0, 0), (.5, .10)]]),
    "3": (.50, [[(0, .86), (.25, 1), (.5, .80), (.16, .54), (.5, .26), (.25, 0), (0, .14)]]),
    "4": (.54, [[(.40, 0), (.40, 1), (0, .30), (.54, .40)]]),
    "5": (.50, [[(.5, 1), (0, .94), (0, .56), (.5, .46), (.5, .14), (.25, 0), (0, .12)]]),
    "6": (.50, [[(.46, 1), (0, .52), (0, .16), (.25, 0), (.5, .16), (.5, .40), (.25, .56), (0, .44)]]),
    "7": (.50, [[(0, .92), (.5, 1), (.14, 0)]]),
    "8": (.50, [[(.25, .52), (0, .76), (.25, 1), (.5, .76), (.25, .52), (0, .26), (.25, 0), (.5, .26), (.25, .52)]]),
    "9": (.50, [[(.5, .56), (.25, .44), (0, .60), (0, .84), (.25, 1), (.5, .84), (.5, .48), (.04, 0)]]),
    # punctuation (runic texts split words with dots, so the dots are diamonds)
    "-": (.36, [[(0, .36), (.36, .46)]]),
    "_": (.56, [[(0, -.12), (.56, -.06)]]),
    "/": (.40, [[(0, -.06), (.40, 1.04)]]),
    "\\": (.40, [[(.40, -.06), (0, 1.04)]]),
    "|": (0, [[(0, -.12), (0, 1.08)]]),
    "'": (0, [[(0, 1), (0, .74)]]),
    '"': (.18, [[(0, 1), (0, .74)], [(.18, 1), (.18, .74)]]),
    "(": (.22, [[(.22, 1.06), (0, .74), (0, .26), (.22, -.06)]]),
    ")": (.22, [[(0, 1.06), (.22, .74), (.22, .26), (0, -.06)]]),
    "[": (.22, [[(.22, 1.04), (0, 1.0), (0, 0), (.22, -.04)]]),
    "]": (.22, [[(0, 1.04), (.22, 1.0), (.22, 0), (0, -.04)]]),
    "+": (.48, [[(.24, .2), (.24, .7)], [(0, .40), (.48, .50)]]),
    "=": (.48, [[(0, .56), (.48, .64)], [(0, .30), (.48, .38)]]),
    "<": (.40, [[(.40, .80), (0, .45), (.40, .10)]]),
    ">": (.40, [[(0, .80), (.40, .45), (0, .10)]]),
    "*": (.46, [[(.23, .96), (.23, .52)], [(.04, .86), (.42, .62)], [(.42, .86), (.04, .62)]]),
    "?": (.46, [[(0, .80), (.23, 1), (.46, .80), (.46, .62), (.23, .46), (.23, .30)]]),
    "#": (.56, [[(.18, 0), (.22, .9)], [(.38, 0), (.42, .9)], [(0, .30), (.56, .38)], [(0, .56), (.56, .64)]]),
    "%": (.60, [[(0, 0), (.60, 1)]]),
    "&": (.60, [[(.60, 0), (.06, .66), (.20, 1), (.38, .80), (0, .30), (.22, 0), (.60, .48)]]),
    "@": (.70, [[(.50, .30), (.46, .66), (.26, .60), (.24, .36), (.46, .30), (.70, .40), (.70, .76), (.42, 1), (0, .74), (0, .26), (.36, 0), (.62, .08)]]),
    "\u2014": (1.0, [[(0, .40), (1.0, .48)]]),          # em dash
    "\u2013": (.60, [[(0, .40), (.60, .46)]]),          # en dash
    "~": (.52, [[(0, .40), (.16, .54), (.36, .40), (.52, .54)]]),
    "`": (.14, [[(0, 1), (.14, .80)]]),
    "^": (.42, [[(0, .70), (.21, 1), (.42, .70)]]),
    "{": (.28, [[(.28, 1.06), (.10, .92), (.10, .58), (0, .50), (.10, .42), (.10, .08), (.28, -.06)]]),
    "}": (.28, [[(0, 1.06), (.18, .92), (.18, .58), (.28, .50), (.18, .42), (.18, .08), (0, -.06)]]),
    "\u2018": (.12, [[(.12, 1), (0, .76)]]),
    "\u2019": (.12, [[(.12, 1), (0, .76)]]),
    "\u201C": (.30, [[(.12, 1), (0, .76)], [(.30, 1), (.18, .76)]]),
    "\u201D": (.30, [[(.12, 1), (0, .76)], [(.30, 1), (.18, .76)]]),
    "\u00B0": (.30, [[(.15, 1), (.30, .85), (.15, .70), (0, .85), (.15, 1)]]),
    "\u00D7": (.42, [[(0, .18), (.42, .66)], [(0, .66), (.42, .18)]]),
    "$": (.48, [[(.48, .86), (.24, .98), (0, .76), (.48, .26), (.24, .02), (0, .14)], [(.24, -.1), (.24, 1.1)]]),
}
DOTS = {  # filled diamonds: (width, [(cx, cy), ...])
    ".": (.16, [(.08, .08)]),
    ":": (.16, [(.08, .08), (.08, .52)]),
    "!": (.16, [(.08, .08)]),
    ",": (.16, [(.08, .08)]),
    ";": (.16, [(.08, .08), (.08, .52)]),
    "%": (.60, [(.10, .86), (.50, .14)]),
    "\u00B7": (.16, [(.08, .45)]),
    "\u2026": (.80, [(.08, .08), (.40, .08), (.72, .08)]),
}
# ᛃ (jera) gets wider-set hooks than the artwork so it can't blur into an S at text sizes
FONT_RUNES = {"Y": (.80, [[(.30, .08), (.04, .34), (.30, .60)], [(.50, .40), (.76, .66), (.50, .92)]])}
EXTRA = {"!": [[(.08, 1), (.08, .32)]], ",": [[(.12, .06), (0, -.18)]], ";": [[(.12, .06), (0, -.18)]]}

RUNE_CP = {"F": 0x16A0, "U": 0x16A2, "TH": 0x16A6, "A": 0x16A8, "R": 0x16B1, "K": 0x16B2,
           "G": 0x16B7, "W": 0x16B9, "H": 0x16BA, "N": 0x16BE, "I": 0x16C1, "Y": 0x16C3,
           "P": 0x16C8, "S": 0x16CB, "B": 0x16D2, "E": 0x16D6, "M": 0x16D7, "L": 0x16DA, "D": 0x16DE}


def outline(polylines, dots, xs, ys):
    """Strokes → filled polygons in font units. xs/ys scale design units."""
    shapes = []
    sw = SW
    for pl in polylines:
        pts = [(SIDE + sw / 2 + x * xs, sw / 2 + y * ys) for x, y in pl]
        if len(pts) > 2 and pts[0] == pts[-1]:
            shapes.append(Polygon(pts).exterior.buffer(sw / 2, join_style=2, mitre_limit=2.2))
        else:
            shapes.append(LineString(pts).buffer(sw / 2, cap_style=3, join_style=2, mitre_limit=2.2))
    for cx, cy in dots:
        x, y = SIDE + sw / 2 + cx * xs, sw / 2 + cy * ys
        r = sw * 0.78
        shapes.append(Polygon([(x, y + r), (x + r * .8, y), (x, y - r), (x - r * .8, y)]))
    return unary_union(shapes) if shapes else None


def draw(geom):
    pen = TTGlyphPen(None)
    if geom is None or geom.is_empty:
        return pen.glyph()
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    for p in polys:
        p = orient(p.simplify(0.5), sign=-1.0)  # exterior clockwise for TrueType
        for ring in [p.exterior, *p.interiors]:
            pts = [(round(x), round(y)) for x, y in ring.coords[:-1]]
            pen.moveTo(pts[0])
            for q in pts[1:]:
                pen.lineTo(q)
            pen.closePath()
    return pen.glyph()


def build(out):
    glyphs, metrics, cmap = {}, {}, {}

    def add(name, cp, width, polylines, dots=(), xs=SCALE, ys=SCALE):
        geom = outline(polylines, dots, xs, ys)
        glyphs[name] = draw(geom)
        adv = round(SIDE * 2 + SW + width * xs)
        lsb = round(geom.bounds[0]) if geom is not None and not geom.is_empty else 0
        metrics[name] = (adv, lsb)
        if cp is not None:
            cmap[cp] = name

    glyphs[".notdef"] = draw(outline([[(0, 0), (0, 1), (.5, 1), (.5, 0), (0, 0)]], (), SCALE, SCALE))
    metrics[".notdef"] = (round(SIDE * 2 + SW + .5 * SCALE), SIDE)
    glyphs["space"] = TTGlyphPen(None).glyph()
    metrics["space"] = (300, 0)
    cmap[0x20] = "space"
    cmap[0xA0] = "space"

    for ch, (w, pls) in L.items():
        dots = DOTS.get(ch, (0, []))[1]
        name = f"uni{ord(ch):04X}"
        add(name, ord(ch), w, pls, dots)
        if "A" <= ch <= "Z":  # small caps for lower case
            add(f"uni{ord(ch.lower()):04X}", ord(ch.lower()), w * 0.86, pls, (),
                xs=SCALE * 0.86, ys=(CAP * SC - SW))
    for ch, (w, dots) in DOTS.items():
        if ch in L:
            continue
        add(f"uni{ord(ch):04X}", ord(ch), w, EXTRA.get(ch, []), dots)
    # Elder Futhark (y-down in art.py → flip)
    for key, cp in RUNE_CP.items():
        w, strokes = FONT_RUNES.get(key, RUNES[key])
        pls = [[(x, 1 - y) for x, y in s] for s in strokes]
        add(f"uni{cp:04X}", cp, w, pls)
    add("uni16EB", 0x16EB, .16, [], [(.08, .45)])  # runic single punctuation ᛫
    add("uni16EC", 0x16EC, .16, [], [(.08, .2), (.08, .7)])  # ᛬

    order = [".notdef", "space"] + sorted(n for n in glyphs if n not in (".notdef", "space"))
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: metrics[n] for n in order})
    fb.setupHorizontalHeader(ascent=900, descent=-250)
    fb.setupNameTable({
        "familyName": "Yggdrasil Runic",
        "styleName": "Regular",
        "uniqueFontIdentifier": "YggdrasilRunic-Regular-1.0",
        "fullName": "Yggdrasil Runic",
        "psName": "YggdrasilRunic-Regular",
        "version": "Version 1.000",
        "copyright": "Yggdrasil OS",
        "licenseDescription": "SIL Open Font License 1.1",
    })
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-250, sTypoLineGap=0,
                usWinAscent=950, usWinDescent=300, sxHeight=round(CAP * SC), sCapHeight=CAP,
                achVendID="YGGD", fsType=0)
    fb.setupPost()
    fb.save(out)
    print(f"wrote {out}: {len(order)} glyphs")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "YggdrasilRunic.ttf")
