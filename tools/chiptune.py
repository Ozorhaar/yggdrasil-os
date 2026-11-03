#!/usr/bin/env python3
"""Tiny NES-style chiptune synth + an arrangement of Grieg's
"In the Hall of the Mountain King" (1875, public domain).

Voices: two pulse-wave channels, a triangle bass, a noise channel for drums.
Like the original, it starts slow and quiet and speeds up and builds every
time round.

    python3 tools/chiptune.py out.wav
"""
import sys
import wave

import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
        "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def freq(n):
    if n is None:
        return 0.0
    name, octave = n[:-1], int(n[-1])
    midi = 12 * (octave + 1) + NOTE[name]
    return 440.0 * 2 ** ((midi - 69) / 12)


# ---------------------------------------------------------------- voices
def pulse(f, n, duty=0.25, vol=1.0, decay=0.0):
    if f == 0:
        return np.zeros(n)
    t = np.arange(n) / SR
    ph = (f * t) % 1.0
    x = np.where(ph < duty, 1.0, -1.0)
    env = np.ones(n)
    a = min(n, int(0.004 * SR))
    env[:a] = np.linspace(0, 1, a)
    if decay:
        env *= np.exp(-decay * t)
    r = min(n, int(0.012 * SR))
    env[-r:] *= np.linspace(1, 0, r)
    return x * env * vol


def triangle(f, n, vol=1.0, gate=1.0):
    if f == 0:
        return np.zeros(n)
    t = np.arange(n) / SR
    ph = (f * t) % 1.0
    x = 4 * np.abs(ph - 0.5) - 1
    x = np.round(x * 7.5) / 7.5          # 4-bit stepped, like the NES
    on = int(n * gate)
    env = np.zeros(n)
    env[:on] = 1
    r = min(on, int(0.01 * SR))
    env[on - r:on] = np.linspace(1, 0, r)
    return x * env * vol


_rng = np.random.default_rng(7)


def noise(n, decay, vol=1.0, tone=1):
    x = _rng.choice([-1.0, 1.0], size=n // tone + 1).repeat(tone)[:n]
    return x * np.exp(-decay * np.arange(n) / SR) * vol


def kick(n, vol=1.0):
    t = np.arange(n) / SR
    f = 160 * np.exp(-25 * t) + 45
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-14 * t) * vol


# ---------------------------------------------------------------- the tune
E8 = 0.5   # an eighth note, in beats

A1 = [("B3", E8), ("C#4", E8), ("D4", E8), ("E4", E8), ("F#4", E8), ("D4", E8), ("F#4", 1)]
A2 = [("F4", E8), ("C#4", E8), ("F4", 1), ("E4", E8), ("C4", E8), ("E4", 1)]
A3 = [("B3", E8), ("C#4", E8), ("D4", E8), ("E4", E8), ("F#4", E8), ("D4", E8), ("F#4", E8), ("B4", E8)]
A4 = [("A4", E8), ("F#4", E8), ("D4", E8), ("F#4", E8), ("A4", 2)]
B1 = [("F#4", E8), ("G#4", E8), ("A#4", E8), ("B4", E8), ("C#5", E8), ("A#4", E8), ("C#5", 1)]
B2 = [("D5", E8), ("A#4", E8), ("D5", 1), ("C#5", E8), ("A#4", E8), ("C#5", 1)]
B4 = [("D5", E8), ("A#4", E8), ("D5", 1), ("C#5", 2)]

# bass: one note per beat, played short (pizzicato)
BA = [["B2", "F#2", "B2", "F#2"], ["C#3", "C#3", "C3", "C3"], ["B2", "F#2", "B2", "F#2"], ["F#2", "A2", "F#2", "F#2"]]
BB = [["F#2", "C#3", "F#2", "C#3"], ["B2", "B2", "F#2", "F#2"], ["F#2", "C#3", "F#2", "C#3"], ["B2", "B2", "F#2", "F#2"]]

SECTION_A = ([A1, A2, A3, A4], BA)
SECTION_B = ([B1, B2, B1, B4], BB)
CYCLE = [SECTION_A, SECTION_A, SECTION_B, SECTION_A]


def transpose(n, octaves):
    return n[:-1] + str(int(n[-1]) + octaves) if n else n


def render(out):
    # each cycle: (bpm start, bpm end, intensity 0..4)
    plan = [(96, 104, 0), (108, 128, 1), (132, 160, 2), (164, 196, 3), (200, 232, 4)]
    tracks = []
    for bpm0, bpm1, level in plan:
        bars = [bar for sec in CYCLE for bar in zip(*sec)]
        nbars = len(bars)
        for bi, (mel, bass) in enumerate(bars):
            bpm = bpm0 + (bpm1 - bpm0) * bi / max(1, nbars - 1)
            beat = 60 / bpm
            n_bar = int(4 * beat * SR)
            lead = np.zeros(n_bar)
            harm = np.zeros(n_bar)
            low = np.zeros(n_bar)
            drums = np.zeros(n_bar)
            vol = 0.22 + 0.13 * level
            # melody
            pos = 0
            for note, beats in mel:
                n = int(beats * beat * SR)
                stacc = 0.55 if level < 2 else 0.8
                body = int(n * (stacc if beats <= E8 else 0.92))
                f = freq(transpose(note, 1 if level >= 3 else 0))
                lead[pos:pos + body] += pulse(f, body, duty=0.25 if level < 4 else 0.125, vol=vol)
                if level >= 1:   # second pulse an octave below (or above at the climax)
                    h = transpose(note, -1 if level < 4 else 1)
                    harm[pos:pos + body] += pulse(freq(h), body, duty=0.5, vol=vol * 0.45)
                pos += n
            # bass + drums, per beat
            for k, bn in enumerate(bass):
                s = int(k * beat * SR)
                n = int(beat * SR)
                gate = 0.35 if level < 3 else 0.6
                low[s:s + n] += triangle(freq(bn if level < 2 else transpose(bn, -1) if level >= 3 else bn),
                                         n, vol=0.5 + 0.1 * level, gate=gate)
                if level >= 2:
                    drums[s:s + n] += kick(n, 0.55) if k % 2 == 0 else noise(n, 28, 0.32)
                    half = int(n / 2)
                    drums[s + half:s + n] += noise(n - half, 90, 0.10, tone=1)
                if level >= 4:   # double-time hats at the climax
                    q = int(n / 4)
                    for j in (1, 3):
                        drums[s + j * q:s + n] += noise(n - j * q, 140, 0.07)[: n - j * q]
            tracks.append(lead + harm + low + drums)
    # ending: three big stabs and a crash
    beat = 60 / 232
    for notes, beats in ((["B3", "F#4", "B4", "B2"], 1), (["B3", "F#4", "B4", "B2"], 1),
                         (["B3", "D4", "F#4", "B1"], 3)):
        n = int(beats * beat * SR)
        hit = sum(pulse(freq(x), n, 0.25, 0.3, decay=1.5) for x in notes[:3])
        hit += triangle(freq(notes[3]), n, 0.8, gate=0.9)
        hit += kick(n, 0.7) + noise(n, 6 if beats > 1 else 20, 0.35)
        tracks.append(hit)
        tracks.append(np.zeros(int(0.5 * beat * SR)))
    x = np.concatenate(tracks)
    x = x / np.max(np.abs(x)) * 0.85
    # gentle low-pass to soften the aliasing a real NES DAC wouldn't have
    x = np.convolve(x, np.ones(3) / 3, mode="same")
    st = (np.stack([x, x], 1) * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())
    print(f"wrote {out}: {len(x) / SR:.1f}s")


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "mountain-king.wav")
