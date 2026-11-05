#!/usr/bin/env python3
"""Realistic Yggdrasil ringtones and alarm, played on real recordings.

Same tunes as phone_sounds.py, but the instruments are real:
  Freyja's Lyre  - celtic harp, one recorded string per note (tune moved up a fourth so the
                   melody lands on the recorded strings)
  Allfather      - a real battle horn (lead) and a deep horn an octave below, bent through the
                   melody by reading the recordings at a varying speed, over the hide drum
  Longship       - hide drum rowing beat, the crew calling each stroke, distant oars and waves, the
                   whole swelling into the deep horn's call

Usage: python realistic_tones.py OUTDIR [names...]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realistic as R  # noqa: E402
from realistic import SR, cut, fade, hits, hp, limit, load, lp, mix, norm, phone_bass, room  # noqa: E402
import synth_hq as H  # noqa: E402

SOURCES = {
    127154: "celtic harp string, B4 (Freyja's Lyre)",
    127155: "celtic harp string, C5 (Freyja's Lyre)",
    127157: "celtic harp string, D5 (Freyja's Lyre)",
    127158: "celtic harp string, E5 (Freyja's Lyre)",
    127159: "celtic harp string, F5 (Freyja's Lyre)",
    127160: "celtic harp string, G5 (Freyja's Lyre)",
    392180: "a battle horn, one long blow (Allfather lead)",
    328541: "a deep horn, one long blow (Allfather second horn, Longship call)",
    85781: "a big native hide drum, struck once (Allfather, Longship)",
    480840: "an oar splash (Longship)",
    551436: "choppy waves against a ship's bow (Longship)",
    57204: "men shouting \"Hey!\" together (Longship crew calls)",
}


def hall(x, rt=1.6, wet=0.3, size=1.3, bright=0.5):
    y = np.concatenate([x, np.zeros(int(rt * SR))])
    return H.in_hall(y, rt, wet, size=size, bright=bright).mean(axis=1)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------ harp
# measured pitch of each recorded string (fractional MIDI note), from autocorrelation
HARP = {127154: 71.03, 127155: 71.95, 127157: 73.94, 127158: 75.95, 127159: 76.68, 127160: 78.78}
_harp_cache = {}


def harp_note(m, ring=2.6):
    """The recorded string closest to MIDI note m, retuned to it exactly."""
    sid = min(HARP, key=lambda s: abs(HARP[s] - m))
    if sid not in _harp_cache:
        x = load(sid)
        _harp_cache[sid] = cut(x, hits(x)[0], 4.0)
    x = _harp_cache[sid]
    y = R.pitch(x, m - HARP[sid])
    return fade(y[: int(ring * SR)], fin=0.001, fout=0.8)


def freyja():
    """The lilting lyre tune, played twice on harp, with low strings on each phrase."""
    up = 5  # up a fourth: D -> G, so the melody sits on the recorded strings
    beat = 0.36
    a = [(69, 1), (74, 1), (72, 1), (69, 2), (67, 1), (69, 1.5), (65, .5), (67, 1), (69, 3)]
    b = [(72, 1), (74, 1), (76, 1), (74, 2), (72, 1), (69, 1.5), (67, .5), (65, 1), (62, 3)]
    parts, t = [], 0.0
    for _ in range(2):
        for phrase in (a, b):
            # low strings: root and fifth, an octave under the tune (soft, so the retuning stays gentle)
            parts.append((t, norm(harp_note(50 + 12 + up, 3.5), 0.38)))
            parts.append((t + beat * 3, norm(harp_note(57 + 12 + up, 3.0), 0.28)))
            for m, d in phrase:
                parts.append((t, norm(harp_note(m + up), 0.9)))
                if d >= 2:  # a third below on the long notes, like a second string ringing
                    parts.append((t + 0.03, norm(harp_note(m + up - 4), 0.4)))
                t += d * beat
    return limit(hall(mix(*parts), 1.8, 0.32, 1.4, 0.55), -8)


# ------------------------------------------------------------------ horns
def sustain(x, t0, t1, total, xf=0.25):
    """A steady stretch of a recording made as long as needed: overlapping crossfaded copies."""
    seg = x[int(t0 * SR):int(t1 * SR)]
    n, k = len(seg), int(xf * SR)
    out = seg.copy()
    w = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    while len(out) < total * SR:
        nxt = seg.copy()
        out[-k:] = out[-k:] * (1 - w) + nxt[:k] * w
        out = np.concatenate([out, nxt[k:]])
    return out


def bend(src, f0, path, dur, release=0.6):
    """Play recording src (pitch f0) through the Hz path over dur seconds by reading it at a
    varying speed, like a player bending a horn from note to note."""
    n = int(dur * SR)
    pts = np.linspace(0, n, len(path))
    f = np.interp(np.arange(n), pts, path)
    pos = np.cumsum(f / f0)
    pos = np.clip(pos, 0, len(src) - 2)
    y = np.interp(pos, np.arange(len(src)), src)
    r = int(release * SR)
    y[-r:] *= np.linspace(1, 0, r) ** 1.5
    return y


_horns = {}


def horns():
    if not _horns:
        lead = load(392180)
        a = hits(lead)[0]
        # attack + body, then extended from its steady middle
        _horns["lead"] = np.concatenate([lead[int(a * SR):int((a + 1.2) * SR)],
                                         sustain(lead, a + 1.2, a + 3.6, 6.0)[int(0.25 * SR):]])
        deep = load(328541)
        d = hits(deep)[0]
        _horns["deep"] = np.concatenate([deep[int(d * SR):int((d + 1.0) * SR)],
                                         sustain(deep, d + 1.0, d + 4.5, 20.0)[int(0.25 * SR):]])
    return _horns["lead"], _horns["deep"]


def drum_strokes():
    nd = load(85781)
    t0 = hits(nd)[0]
    return fade(cut(nd, t0, 0.35), fout=0.12), fade(cut(nd, t0, 1.2), fout=0.6)


def phone_drum(dry):
    """The hide drum voiced for a phone speaker (same treatment as the War Drums notification)."""
    from scipy.signal import butter, sosfilt
    body = phone_bass(dry, 1.6)
    edge = sosfilt(butter(2, [700, 2500], "band", fs=SR, output="sos"), np.tanh(8 * norm(dry)))
    k = int(0.004 * SR)
    env = np.convolve(np.abs(dry), np.ones(k) / k, "same")
    edge = edge * (env / (env.max() + 1e-12)) ** 1.5
    y = sosfilt(butter(4, 120, "high", fs=SR, output="sos"), norm(body) + 0.45 * norm(edge))
    return np.tanh(3.0 * norm(y)) / np.tanh(3.0)


def allfather():
    """A slow, stately horn call, two horns an octave apart, the hide drum keeping time."""
    lead, deep = horns()
    beat = 0.75
    calls = [(0, [147, 147, 146], 1.3), (2, [196, 220, 220, 219], 2.0),
             (5, [175, 175], 0.8), (6, [196, 196], 0.8), (7, [220, 220, 220], 2.2),
             (10, [147, 147], 1.0), (11.5, [220, 294, 294, 293], 3.2)]
    hparts = []
    for b, fz, d in calls:
        hparts.append((b * beat, norm(bend(lead, 304.0, fz, d), 0.85)))
        hparts.append((b * beat + 0.02, norm(phone_bass(bend(deep, 55.0, [f / 2 for f in fz], d), 0.6), 0.55)))
    hornline = mix(*hparts)
    short, _ = drum_strokes()
    dparts = [(i * beat, norm(short, 1.0 if i % 4 == 0 else 0.55)) for i in range(20)]
    drums = phone_drum(mix(*dparts))
    n = max(len(hornline), len(drums))
    both = np.zeros(n)
    both[:len(hornline)] += norm(hornline, 1.0)
    both[:len(drums)] += norm(drums, 0.6)
    return limit(hall(both, 2.0, 0.3, 1.5, 0.45), -9)


# ------------------------------------------------------------------ longship
def crew_call(shout, k):
    """One shout made into a ship's crew: a few copies, slightly different pitch and timing,
    pitched down a touch for bigger chests."""
    rng = np.random.default_rng(1000 + k)
    voices = [(0.0, 0.0, 1.0), (0.014, -2.0, 0.8), (0.027, 1.0, 0.65), (0.04, -3.5, 0.55)]
    parts = [(dt + rng.uniform(0, 0.006), norm(R.pitch(shout, ps - 1.0 + rng.uniform(-0.4, 0.4)), g))
             for dt, ps, g in voices]
    return hp(mix(*parts), 140)


def longship():
    """The rowing beat starts slow and soft and swells: the drum on every stroke and the crew
    calling it, a lighter beat on the recovery; then the deep horn calls over the last strokes."""
    total = 22.0
    short, big = drum_strokes()
    hv = load(57204)
    shout = fade(cut(hv, 0.04, 0.42, pre=0), fin=0.004, fout=0.12)
    sp = load(480840)
    splash = fade(cut(sp, 0.0, 0.7), fout=0.3)
    splash = lp(splash, 2500)                     # duller and further off: water, not a slap

    drum_p, crew_p, splash_p = [], [], []
    t, k = 0.0, 0
    while t < total:
        p = t / total
        bpm = 46 + 74 * p ** 1.3                  # 46 -> 120 beats a minute
        vol = 0.5 + 0.5 * p
        if k % 2 == 0:                            # the stroke: drum, the crew calls it, oars bite
            drum_p.append((t, norm(short, vol)))
            crew_p.append((t + 0.01, norm(crew_call(shout, k), 0.55 + 0.45 * p)))
            splash_p.append((t + 0.12, norm(splash, vol)))
        else:                                     # the recovery: a lighter beat
            drum_p.append((t, norm(short, vol * 0.5)))
        t += 60 / bpm
        k += 1
    # the horn calls over the last strokes; the crew answers on the final big beat
    _, deep = horns()
    call = np.concatenate([bend(deep, 55.0, [98, 110, 110, 110], 1.4, 0.35), np.zeros(int(0.12 * SR)),
                           bend(deep, 55.0, [110, 147, 147, 146], 2.4, 0.9)])
    call = phone_bass(call, 0.6)
    for i in range(4):
        drum_p.append((total + 0.2 + i * 0.5, norm(big if i == 3 else short, 1.0)))
    crew_p.append((total + 0.2 + 1.5 + 0.01, norm(crew_call(shout, 999), 1.0)))

    drums = phone_drum(mix(*drum_p))
    sea = load(551436)
    end = total + 4.5
    bed = sea[: int(end * SR)]
    bed = hp(lp(bed, 5000), 150) * np.linspace(0.4, 0.8, len(bed))
    bed = fade(bed, fin=1.5, fout=2.0)

    layers = [(0.0, norm(drums, 0.85)), (0.0, norm(limit(mix(*crew_p), -4), 1.0)),
              (0.0, norm(mix(*splash_p), 0.05)),
              (0.0, norm(bed, 0.12)), (total + 0.2, norm(call, 0.95))]
    return limit(hall(mix(*layers), 1.3, 0.2, 1.3, 0.45), -9)


TONES = {
    "Ringtones/Yggdrasil - Freyja's Lyre.ogg": (freyja, 0.9),
    "Ringtones/Yggdrasil - Allfather.ogg": (allfather, 0.9),
    "Alarms/Yggdrasil - Longship.ogg": (longship, 0.92),
}


def credits_block():
    lines = ["", "Ringtones and alarm (realistic_tones.py):", ""]
    for sid, what in SOURCES.items():
        R.fetch(sid)
        import json
        m = json.load(open(os.path.join(R.CACHE, f"{sid}.json")))
        lines.append(f'- {what}: "{m["name"]}" by {m["user"]}, {m["license"]}, {m["url"]}')
    return "\n".join(lines) + "\n"


SOUNDFONT_NOTICE = """
Mountain King (mountain_king_orch.py) is Grieg's "In the Hall of the Mountain King" (1875, public
domain), rendered with FluidSynth and the MuseScore General soundfont (MIT licence), whose notices
must travel with derivative works:

- FluidR3 (original version) by Frank Wen, Copyright (c) 2000-02
- Mono conversion (FluidR3Mono) by Michael Cowgill, Copyright (c) 2014-17
- Adaptation for MuseScore_General.sf2 by S. Christian Collins, Copyright (c) 2018-19
- Temple Blocks instrument provided by Ethan Winer, Copyright (c) 2002
- Drumline Cymbals provided by Michael Schorsch, Copyright (c) 2016
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "phone-sounds"
    want = sys.argv[2:]
    for name, (fn, peak) in TONES.items():
        if want and not any(w.lower() in name.lower() for w in want):
            continue
        R.write(os.path.join(out, name), fn(), peak)
    if not want or any("mountain" in w.lower() for w in want):
        import mountain_king_orch
        mountain_king_orch.render(os.path.join(out, "Ringtones", "Yggdrasil - Mountain King.ogg"))
    # one credits file for everything: notifications (realistic.py) + these
    R.credits(out)
    with open(os.path.join(out, "CREDITS.md"), "a") as f:
        f.write(credits_block() + SOUNDFONT_NOTICE)


if __name__ == "__main__":
    main()
