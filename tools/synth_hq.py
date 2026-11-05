#!/usr/bin/env python3
"""Higher-quality synthesis for the Yggdrasil sounds: physical (modal) models of a big war
drum, two rune stones knocked together and a long watch horn, played into a stereo hall.

    ~/.venvs/ygg-sounds/bin/python tools/synth_hq.py OUTDIR

Writes OUTDIR/HQ - War Drums.ogg, HQ - Rune Stone.ogg, HQ - Heimdall.ogg (stereo).
Nothing sampled; seeded, so it renders the same every time.
"""
import os
import sys

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
from phone_sounds import FFMPEG  # noqa: E402
import subprocess  # noqa: E402

SR = 48000
RNG = np.random.default_rng(11)


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def lowpass(x, hz, order=2):
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def highpass(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


# ------------------------------------------------------------------ the hall
def hall_ir(rt60, size=1.0, bright=0.6, seed=3):
    """A stereo impulse response: early reflections, then a dense tail whose highs die
    faster than its lows, the left and right decorrelated."""
    rng = np.random.default_rng(seed)
    n = int((rt60 * 1.2 + 0.1) * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        noise = rng.standard_normal(n)
        lo = lowpass(noise, 900) * np.exp(-6.9 * t / rt60)
        mid = bandpass(noise, 900, 4000) * np.exp(-6.9 * t / (rt60 * 0.7))
        hi = highpass(noise, 4000) * np.exp(-6.9 * t / (rt60 * 0.35)) * bright
        tail = (lo + mid * 0.8 + hi * 0.5)
        pre = int(0.012 * size * SR)
        tail[:pre] = 0
        tail[pre:pre + int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))
        early = np.zeros(n)
        for d, g in ((0.007, 0.6), (0.013, 0.45), (0.019, 0.38), (0.026, 0.3), (0.034, 0.22), (0.047, 0.16)):
            k = int((d * size + rng.uniform(-0.001, 0.001)) * SR)
            early[k] += g * (1 if rng.random() > 0.5 else -1)
        ir = early + tail / np.sqrt(np.sum(tail ** 2) + 1e-12) * 0.9
        ir[0] = 1.0
        out.append(ir)
    return out


def in_hall(x, rt60, wet, size=1.0, bright=0.6):
    irs = hall_ir(rt60, size, bright)
    l = fftconvolve(x, irs[0])[: len(x) + int(rt60 * SR)]
    r = fftconvolve(x, irs[1])[: len(x) + int(rt60 * SR)]
    dry = np.zeros_like(l)
    dry[: len(x)] = x
    wl, wr = l - dry, r - dry      # wet only
    s = max(np.abs(wl).max(), np.abs(wr).max()) + 1e-12
    return np.stack([dry + wet * wl / s * np.abs(x).max(), dry + wet * wr / s * np.abs(x).max()], 1)


# ------------------------------------------------------------------ war drum
MEMBRANE = (1.000, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501, 3.600, 3.652)


def war_drum_hit(f0=58.0, vel=1.0, dur=1.6, seed=0):
    """A big rope-tensioned war drum struck near the centre with a felt mallet.
    Membrane modes (with the air-loaded fundamental), a pitch drop as the skin settles,
    the mallet's thump and a little shell ring."""
    rng = np.random.default_rng(seed)
    t = t_(dur)
    glide = 1 + 0.09 * vel * np.exp(-t / 0.05)            # struck harder -> starts sharper
    x = np.zeros_like(t)
    for i, r in enumerate(MEMBRANE):
        f = f0 * r * (1.0 if i else 1.0)
        amp = (1.0 if i == 0 else 0.55 / (i ** 0.9)) * (0.6 + 0.4 * vel)
        decay = (0.45 if i == 0 else 0.25 / (1 + 0.6 * i)) * (0.8 + 0.4 * vel)
        ph = 2 * np.pi * np.cumsum(f * glide) / SR + rng.uniform(0, 2 * np.pi)
        x += amp * np.sin(ph) * np.exp(-t / decay)
    thump = lowpass(rng.standard_normal(len(t)), 160, 4) * np.exp(-t / 0.025) * 1.2 * vel
    slap = bandpass(rng.standard_normal(len(t)), 300, 900) * np.exp(-t / 0.006) * 0.12 * vel ** 1.5
    shell = bandpass(rng.standard_normal(len(t)), 140, 320, 4) * np.exp(-t / 0.10) * 0.25
    y = x + thump + slap + shell
    y[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return lowpass(y, 1400, 4)            # a felt mallet on a big skin: no fizz


def war_drums():
    """DUM . DUM-DUM . DUM! on two big drums, in a timber hall."""
    pat = ((0.00, 56, 1.00, 1), (0.50, 62, 0.75, 2), (0.74, 62, 0.85, 3), (1.10, 54, 1.0, 4))
    n = int(3.2 * SR)
    x = np.zeros(n)
    for at, f0, v, s in pat:
        h = war_drum_hit(f0, v, 2.0 if at > 1 else 1.4, s)
        k = int(at * SR)
        x[k:k + len(h)] += h[: n - k] * v
    low = lowpass(x, 150, 4)
    harm = bandpass(np.tanh(4 * low / (np.abs(low).max() + 1e-12)), 150, 600)
    x = x / np.abs(x).max() + 0.42 * harm / (np.abs(harm).max() + 1e-12)   # audible on a phone speaker
    x = highpass(x, 90, 4)                                                  # what a phone can't play only eats loudness
    return in_hall(x, rt60=1.2, wet=0.18, size=1.2, bright=0.25)


# ------------------------------------------------------------------ rune stones
def stone_knock(f0, seed, hard=1.0):
    """Two hand-sized stones knocked together: a hard click, a short inharmonic ring
    (stone modes die within tens of ms) and a dull body thud."""
    rng = np.random.default_rng(seed)
    t = t_(0.35)
    ratios = (1.0, 1.52, 2.27, 2.95, 3.83, 4.71, 6.04)
    ring = np.zeros_like(t)
    for i, r in enumerate(ratios):
        f = f0 * r * rng.uniform(0.98, 1.02)
        ring += (1 / (1 + 0.7 * i)) * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / (0.035 / (1 + 0.35 * i)))
    click = bandpass(rng.standard_normal(len(t)), 2000, 6000) * np.exp(-t / 0.001) * 0.35 * hard
    grit = bandpass(rng.standard_normal(len(t)), 1200, 4000) * np.exp(-t / 0.004) * 0.15
    thud = lowpass(rng.standard_normal(len(t)), 450, 4) * np.exp(-t / 0.015) * 1.6
    y = ring * 1.0 + click + grit + thud
    return y / np.abs(y).max()


def rune_stone():
    a = stone_knock(1450, 1, 1.0)
    b = stone_knock(1720, 2, 0.8)
    x = np.zeros(int(0.9 * SR))
    x[: len(a)] += a * 0.85
    k = int(0.19 * SR)
    x[k:k + len(b)] += b
    return in_hall(x, rt60=0.6, wet=0.2, size=0.6, bright=0.4)


# ------------------------------------------------------------------ watch horn
def watch_horn(f0=98.0, dur=2.6):
    """A long cow-horn / lur note: lips buzzing into a conical bore. A jittery pulse source,
    brightness that grows with breath, the bore's resonances, breath noise and a gentle swell."""
    rng = np.random.default_rng(5)
    t = t_(dur)
    swell = np.clip(t / 0.35, 0, 1) ** 1.5 * np.clip((dur - t) / 0.6, 0, 1) ** 1.2
    scoop = 1 - 0.035 * np.exp(-t / 0.12)                           # lips find the note
    vib = 1 + 0.004 * np.sin(2 * np.pi * 4.6 * t + 0.4) * np.clip((t - 0.6) / 0.6, 0, 1)
    jitter = 1 + 0.0025 * lowpass(rng.standard_normal(len(t)), 30)
    f = f0 * scoop * vib * jitter
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.zeros_like(t)
    for h in range(1, 28):
        # brighter as breath grows; odd/even balance of a conical horn
        tilt = np.exp(-h / (2.2 + 9 * swell))
        x += tilt * np.sin(h * ph + 0.3 * h) * (1.0 if h % 2 else 0.8)
    # bore and bell: a few broad resonances, then the bell's high-pass
    body = (bandpass(x, 180, 420) * 1.0 + bandpass(x, 520, 900) * 0.7 + bandpass(x, 1100, 1900) * 0.35 + lowpass(x, 180) * 0.6)
    body = highpass(body, 70)
    breath = bandpass(rng.standard_normal(len(t)), 900, 4500) * 0.035 * swell
    y = (body + breath) * swell
    y = np.tanh(1.4 * y / (np.abs(y).max() + 1e-12)) / np.tanh(1.4)
    return in_hall(y, rt60=2.6, wet=0.45, size=2.0, bright=0.35)


def write_stereo(path, st, peak=0.9):
    st = st / (np.abs(st).max() + 1e-12) * peak
    tail = np.nonzero(np.abs(st).max(1) > 0.003)[0]
    st = st[: tail[-1] + int(0.05 * SR)] if len(tail) else st
    fade = int(0.04 * SR)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    pcm = (st * 32767).astype(np.int16)
    title = os.path.splitext(os.path.basename(path))[0]
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "libvorbis", "-q:a", "6", "-metadata", f"title={title}", "-metadata", "artist=Yggdrasil", path],
                   input=pcm.tobytes(), check=True)
    print(f"{os.path.basename(path)}: {len(st) / SR:.2f}s")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    write_stereo(os.path.join(out, "HQ - War Drums.ogg"), war_drums(), 0.95)
    write_stereo(os.path.join(out, "HQ - Rune Stone.ogg"), rune_stone(), 0.9)
    write_stereo(os.path.join(out, "HQ - Heimdall.ogg"), watch_horn(), 0.9)


if __name__ == "__main__":
    main()
