#!/usr/bin/env python3
"""Grieg's "In the Hall of the Mountain King" (1875, public domain) for sampled orchestra.

Same notes and the same accelerando as the chiptune ringtone (chiptune.py), arranged the way
Grieg builds it: bassoons over pizzicato cellos and basses, then plucked violins join, then the
strings take up their bows with horns and timpani, and the last time round everyone plays,
brass and cymbals included.

Rendered with FluidSynth and the MuseScore General soundfont (MIT licence; Debian's
musescore-general-soundfont 0.2-3 package, checked against Debian's archive index).

    python mountain_king_orch.py OUT.ogg
"""
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiptune as C  # noqa: E402  (the tune: A1..B4, BA/BB, CYCLE)
import realistic as R  # noqa: E402

SF = os.path.expanduser("~/.local/share/soundfonts/MuseScore_General_Full.sf3")
SF_SHA256 = "d8268fe5484b12adaa90cc382138ae8ed9cd3253d5e3ad72b3bcf361a107c1fd"
TPQ = 480


def midi_num(n):
    name, octave = n[:-1], int(n[-1])
    return 12 * (octave + 1) + C.NOTE[name]


def vlq(v):
    out = [v & 0x7F]
    v >>= 7
    while v:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    return bytes(reversed(out))


class Track:
    def __init__(self):
        self.ev = []  # (tick, order, bytes)

    def add(self, tick, data, order=1):
        self.ev.append((int(tick), order, bytes(data)))

    def note(self, tick, ch, n, vel, dur):
        self.add(tick, [0x90 | ch, n, max(1, min(127, int(vel)))], 1)
        self.add(tick + max(1, int(dur)), [0x80 | ch, n, 0], 0)

    def program(self, tick, ch, prog):
        self.add(tick, [0xC0 | ch, prog], -1)

    def cc(self, tick, ch, num, val):
        self.add(tick, [0xB0 | ch, num, int(val)], -1)

    def tempo(self, tick, bpm):
        us = int(60_000_000 / bpm)
        self.add(tick, [0xFF, 0x51, 0x03, (us >> 16) & 0xFF, (us >> 8) & 0xFF, us & 0xFF], -2)

    def bytes(self):
        out, last = b"", 0
        for tick, _, data in sorted(self.ev, key=lambda e: (e[0], e[1])):
            out += vlq(tick - last) + data
            last = tick
        out += vlq(0) + b"\xFF\x2F\x00"
        return b"MTrk" + struct.pack(">I", len(out)) + out


# channels and General MIDI programs
BSN, PIZZ, STR, HORN, TIMP, BRASS, CELLO, PERC = 0, 1, 2, 3, 4, 5, 6, 9
PROGRAMS = {BSN: 70, PIZZ: 45, STR: 48, HORN: 60, TIMP: 47, BRASS: 61, CELLO: 45}


def arrange(bpm0=112, bpm1=216):
    t = Track()
    for ch, p in PROGRAMS.items():
        t.program(0, ch, p)
        t.cc(0, ch, 91, 50)   # reverb send
        t.cc(0, ch, 7, 110)
    bars = [bar for sec in C.CYCLE for bar in zip(*sec)]
    tick = 0
    for bi, (mel, bass) in enumerate(bars):
        bpm = bpm0 + (bpm1 - bpm0) * bi / (len(bars) - 1)
        t.tempo(tick, bpm)
        stage = bi // 4                                  # 0..3: one stage per time through the A/B line
        dyn = 52 + 18 * stage + 3 * (bi % 4)              # crescendo through the whole thing
        # melody
        pos = tick
        for note, beats in mel:
            n = midi_num(note)
            dur = beats * TPQ
            short = dur * (0.55 if beats <= C.E8 and stage < 2 else 0.85)
            t.note(pos, BSN, n, dyn, short)                        # bassoons always lead
            if stage >= 1:
                t.note(pos, PIZZ, n + 12, dyn - 6, short * 0.6)           # plucked violins an octave up
            if stage >= 2:
                t.note(pos, STR, n + 12, dyn, short)                      # bowed strings
                t.note(pos, HORN, n, dyn - 8, short)
            if stage >= 3:
                t.note(pos, STR, n + 24, dyn, short)
                t.note(pos, BRASS, n, dyn + 4, short)
            pos += dur
        # bass line, one note per beat, plucked; timpani from stage 2
        for k, bn in enumerate(bass):
            s = tick + k * TPQ
            b = midi_num(bn)
            t.note(s, CELLO, b, dyn + 4, TPQ * 0.4)
            t.note(s, CELLO, b - 12, dyn, TPQ * 0.4)
            if stage >= 2:
                t.note(s, TIMP, b, dyn + (8 if k % 2 == 0 else 0), TPQ * 0.6)
            if stage >= 3:
                t.note(s, PERC, 36 if k % 2 == 0 else 38, dyn - 10, TPQ * 0.3)   # bass drum / snare
                if k == 0:
                    t.note(s, PERC, 49, dyn - 6, TPQ)                           # crash on the downbeat
        tick += 4 * TPQ
    # the last chord: B minor, everyone, with a cymbal
    for n in (47, 54, 59, 62, 66, 71):
        for ch in (STR, HORN, BRASS):
            t.note(tick, ch, n + (12 if ch == STR else 0), 112, TPQ * 2.2)
    for ch, n in ((CELLO, 35), (CELLO, 47), (TIMP, 47)):
        t.note(tick, ch, n, 120, TPQ * 1.5)
    t.note(tick, PERC, 49, 115, TPQ * 2)
    t.note(tick, PERC, 36, 120, TPQ)
    t.tempo(tick, bpm1)
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, TPQ) + t.bytes()


def check_soundfont():
    import hashlib
    h = hashlib.sha256()
    with open(SF, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != SF_SHA256:
        raise SystemExit(f"soundfont checksum mismatch: {SF}")


def render(out):
    check_soundfont()
    with tempfile.TemporaryDirectory() as d:
        mid, wav = os.path.join(d, "mk.mid"), os.path.join(d, "mk.wav")
        open(mid, "wb").write(arrange())
        subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.8", "-r", str(R.SR), "-o", "synth.reverb.room-size=0.7",
                        "-o", "synth.reverb.level=0.5", "-F", wav, SF, mid], check=True)
        raw = subprocess.run([R.FFMPEG, "-loglevel", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", str(R.SR), "-"],
                             capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    nz = np.where(np.abs(x) > 1e-4)[0]
    x = x[: nz[-1] + int(0.05 * R.SR)]              # trim the silent tail
    song = sum(4 * 60 / (112 + (216 - 112) * i / 15) for i in range(16))
    x = x[: int((song + 2.8) * R.SR)]               # let the last chord ring, but not so long the loop stalls
    x = R.fade(x, fin=0.002, fout=0.6)
    x = R.hp(x, 70)                                  # nothing a phone can play lives below this
    x = R.limit(x, -8)
    R.write(out, x, 0.9)


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "Yggdrasil - Mountain King.ogg")
