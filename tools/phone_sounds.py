#!/usr/bin/env python3
"""Synthesises the Yggdrasil phone sound set from scratch (nothing sampled).

    python3 tools/phone_sounds.py OUTDIR

Writes .ogg files:
  Ringtones/      Yggdrasil - Mountain King.ogg   chiptune Grieg, speeding up (calls)
  Notifications/  Yggdrasil - Mjolnir.ogg         hammer crack + thunder (texts)
                  Yggdrasil - Ravens.ogg          Huginn and Muninn, two calls (email)
                  Yggdrasil - Heimdall.ogg        one low watch-horn note (Home Assistant / Frigate)
                  Yggdrasil - War Horn.ogg        three hard blasts (PagerDuty / urgent)
                  Yggdrasil - Rune Stone.ogg      two soft stone taps (calendar / reminders)
                  Yggdrasil - War Drums.ogg       DUM . DUM-DUM . DUM (everything else)
  Ringtones/      Yggdrasil - Freyja's Lyre.ogg   a warm lyre tune over a drone (one person's calls)
                  Yggdrasil - Allfather.ogg       slow horn call over the war drums (another's calls)
  Alarms/         Yggdrasil - Longship.ogg        rowing drum that speeds up, then a horn
  Keys/           rune_tap / rune_space / rune_delete / rune_enter (.ogg) for Yggdrasil Keys
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
import chiptune  # noqa: E402
from sounds import SR, env, horn, reverb  # noqa: E402

RNG = np.random.default_rng(7)

# The .ogg files need ffmpeg's libvorbis encoder. Homebrew's plain ffmpeg doesn't have it on
# the Mac mini, so prefer the keg-only ffmpeg-full there; $FFMPEG overrides both.
FFMPEG = os.environ.get("FFMPEG") or next(
    (p for p in ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",) if os.path.exists(p)), "ffmpeg")


def lp(x, hz, order=4):
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def hp(x, hz, order=4):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def silence(sec):
    return np.zeros(int(sec * SR))


def mix(*parts):
    """Overlay (offset_seconds, signal) pairs."""
    end = max(int(o * SR) + len(x) for o, x in parts)
    out = np.zeros(end)
    for o, x in parts:
        s = int(o * SR)
        out[s:s + len(x)] += x
    return out


def norm(x, peak):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


# ------------------------------------------------------------------ Mjölnir
def mjolnir():
    """A sharp crack of the hammer, a metallic ring, then thunder rolling away."""
    # crack: a very fast, bright noise burst
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    crack = hp(RNG.standard_normal(n), 1800) * np.exp(-55 * t)
    crack += 0.8 * RNG.standard_normal(n) * np.exp(-400 * t)
    # metal: inharmonic ring off the hammer head
    n2 = int(0.9 * SR)
    t2 = np.arange(n2) / SR
    ring = sum(a * np.sin(2 * np.pi * 1350 * r * t2) * np.exp(-d * t2)
               for r, a, d in ((1, .5, 9), (1.73, .35, 12), (2.62, .25, 16), (4.1, .15, 22)))
    # thunder: a deep rumble for good speakers, plus a rolling mid-range growl
    # that phone speakers (which can't do real bass) can still play
    n3 = int(2.3 * SR)
    t3 = np.arange(n3) / SR
    brown = hp(np.cumsum(RNG.standard_normal(n3)), 25, 2)
    deep = norm(lp(brown, 260), 1.0)
    growl = norm(bp(RNG.standard_normal(n3), 160, 900, 2), 1.0)
    shape = (1 - np.exp(-t3 / 0.09)) * np.exp(-t3 / 0.85)
    rolls = 1 + 0.8 * np.clip(np.sin(2 * np.pi * 2.6 * t3 + 0.6), 0, None) * np.exp(-t3 / 0.9) \
        + 0.5 * np.clip(np.sin(2 * np.pi * 4.7 * t3 + 2.0), 0, None)
    rumble = norm((deep * 0.9 + growl * 0.75) * shape * rolls, 1.0)
    crackle = lp(hp(RNG.standard_normal(n3), 500), 3000) * np.exp(-t3 / 0.22) * 0.3
    boom = bp(RNG.standard_normal(int(0.35 * SR)), 120, 700) * np.exp(-np.arange(int(0.35 * SR)) / SR * 14)
    x = mix((0, norm(crack, 1.0)), (0.0, norm(ring, 0.45)), (0.01, norm(boom, 0.8)),
            (0.04, rumble * 0.9), (0.04, crackle))
    x = np.tanh(1.8 * norm(x, 1.0))                    # squeeze it so the thunder holds up next to the crack
    return reverb(x * env(len(x), 0.0005, 0.25), 0.35)


# ------------------------------------------------------------------ ravens
def caw(f0=560, dur=0.30, seed=0):
    """One raven call: a harsh, nasal 'kraa' that bends down at the end."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    jitter = lp(rng.standard_normal(n), 40, 2)
    jitter = jitter / (np.max(np.abs(jitter)) + 1e-9)
    contour = f0 * (1.05 - 0.14 * (t / dur) ** 1.5) * (1 + 0.06 * jitter)
    ph = 2 * np.pi * np.cumsum(contour) / SR
    # a buzzy source: many harmonics, roughened by fast amplitude flutter
    src = sum((1 / h ** 0.7) * np.sin(h * ph + rng.uniform(0, 6)) for h in range(1, 18))
    # croaky: irregular pulses (half the cycles weaker, like a rasping throat) and lots of breath
    sub = 1 + 0.9 * np.sign(np.sin(ph / 2))
    rough = (1 + 0.8 * np.sin(2 * np.pi * 85 * t + rng.uniform(0, 6))) * (0.55 + 0.45 * sub) \
        + 0.5 * rng.standard_normal(n)
    src = src * rough + 1.6 * rng.standard_normal(n)
    # beak/throat formants
    voiced = 1.0 * bp(src, 900, 1500) + 0.8 * bp(src, 1800, 2600) + 0.35 * bp(src, 3000, 4200)
    shape = np.clip(t / 0.03, 0, 1) * np.clip((dur - t) / 0.09, 0, 1) ** 0.8
    return np.tanh(2.2 * norm(voiced * shape, 1.0)) * shape


def ravens():
    """Huginn and Muninn: two calls, the second a little lower and further off."""
    first = caw(560, 0.30, 1)
    second = caw(500, 0.34, 2) * 0.8
    x = np.concatenate([first, silence(0.16), lp(second, 5000)])
    return reverb(x, 0.45)


# ------------------------------------------------------------------ Heimdall
def heimdall():
    """One long, low watch-horn note: something is at the bridge."""
    x = horn([100, 110, 110, 110, 109], 1.6)
    x = np.tanh(1.5 * x) + 0.35 * hp(x, 500)          # keep it deep but give a phone speaker something to play
    return reverb(x, 0.55)


# ------------------------------------------------------------------ war horn
def war_horn():
    """Three hard, short blasts: call to arms."""
    def blast(d):
        x = horn([104, 147, 147, 146], d, attack=0.04, release=0.12 if d < 0.6 else 0.4)
        return np.tanh(2.0 * x)
    x = np.concatenate([blast(0.42), silence(0.10), blast(0.42), silence(0.10), blast(0.85)])
    return reverb(x, 0.35)


# ------------------------------------------------------------------ rune stone
def stone_tap(f0, seed):
    """Stone on stone: a dull click with a short, gritty, inharmonic body."""
    rng = np.random.default_rng(seed)
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    body = sum(a * np.sin(2 * np.pi * f0 * r * t + rng.uniform(0, 6)) * np.exp(-d * t)
               for r, a, d in ((1, 1, 60), (1.47, .7, 75), (2.31, .45, 95), (3.86, .25, 130)))
    knock = bp(rng.standard_normal(n), f0 * 0.6, f0 * 2.2) * np.exp(-70 * t) * 1.4
    grit = bp(rng.standard_normal(n), 1800, 6500) * np.exp(-110 * t) * 0.7
    click = rng.standard_normal(n) * np.exp(-1200 * t) * 0.6
    return (body + knock + grit + click) * env(n, 0.0005, 0.05)


def rune_stone():
    a = norm(stone_tap(620, 1)[:int(0.16 * SR)], 1.0)
    b = norm(stone_tap(780, 2), 0.9)
    x = np.concatenate([a, silence(0.07), b])
    return reverb(np.tanh(2.2 * x), 0.3)


# ------------------------------------------------------------------ longship alarm
def drum(f0=95, vol=1.0, seed=0):
    """A big rowing drum: pitch drops as the skin settles."""
    rng = np.random.default_rng(seed)
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = f0 * (0.72 + 0.28 * np.exp(-t * 18))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * np.exp(-5.5 * t) + 0.5 * np.sin(1.59 * ph) * np.exp(-8 * t) \
        + 0.45 * np.sin(2.14 * ph) * np.exp(-11 * t) + 0.3 * np.sin(2.65 * ph) * np.exp(-14 * t)
    tone = np.tanh(1.8 * tone)                     # a bit of grit so it carries on small speakers
    skin = bp(rng.standard_normal(n), 300, 1800) * np.exp(-24 * t) * 1.3
    beater = bp(rng.standard_normal(n), 1200, 3500) * np.exp(-140 * t) * 0.8
    shell = np.sin(2 * np.pi * f0 * 3.6 * t) * np.exp(-20 * t) * 0.5
    return np.tanh(1.4 * (tone + skin + beater + shell)) * vol * env(n, 0.001, 0.08)


def longship():
    """The rowing beat starts slow and soft, quickens and swells, then the horn calls."""
    parts = []
    t = 0.0
    total = 22.0
    k = 0
    while t < total:
        p = t / total
        bpm = 46 + 74 * p ** 1.3                  # 46 -> 120 strokes a minute
        vol = 0.4 + 0.6 * p
        accent = 1.0 if k % 2 == 0 else 0.6       # stroke - recover
        parts.append((t, drum(140 if k % 2 == 0 else 158, vol * accent, k)))
        t += 60 / bpm
        k += 1
    call = np.concatenate([horn([98, 110, 110, 110], 1.4), silence(0.12), horn([110, 147, 147, 146], 2.2)])
    parts.append((total + 0.2, call * 0.9))
    for i in range(4):  # drums keep pulling under the horn
        parts.append((total + 0.2 + i * 0.5, drum(140, 1.0, 100 + i)))
    return reverb(mix(*parts), 0.4)


# ------------------------------------------------------------------ default notification
def war_drums():
    """The everything-else alert: DUM . DUM-DUM . DUM! on the big war drums."""
    hits = [(0.00, 128, 0.80), (0.46, 140, 0.60), (0.66, 140, 0.70), (1.08, 112, 1.00)]
    parts = [(t, drum(f, v, 40 + i)) for i, (t, f, v) in enumerate(hits)]
    parts.append((1.08, drum(170, 0.45, 60)))     # a second drummer lands the last stroke with you
    return reverb(mix(*parts), 0.35)


# ------------------------------------------------------------------ contact ringtones
def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(f0, dur=2.2, bright=0.6, seed=0):
    """A lyre string (Karplus-Strong), warm rather than twangy."""
    n = int(dur * SR)
    p = max(2, int(round(SR / f0)))
    rng = np.random.default_rng(seed)
    buf = lp(rng.uniform(-1, 1, p * 4), 900 + 3000 * bright, 2)[-p:]
    out = np.zeros(n)
    for i in range(n):
        v = buf[i % p]
        out[i] = v
        buf[i % p] = 0.996 * 0.5 * (v + buf[(i + 1) % p])
    body = bp(out, 150, 2400)
    return (0.7 * out + 0.5 * body) * env(n, 0.002, 0.3)


def freyja():
    """A lilting tune on the lyre over a soft open-fifth drone, played through twice."""
    beat = 0.36
    a = [(69, 1), (74, 1), (72, 1), (69, 2), (67, 1), (69, 1.5), (65, .5), (67, 1), (69, 3)]
    b = [(72, 1), (74, 1), (76, 1), (74, 2), (72, 1), (69, 1.5), (67, .5), (65, 1), (62, 3)]
    parts, t, k = [], 0.0, 0
    for _ in range(2):
        for phrase, root in ((a, 50), (b, 50)):
            parts.append((t, pluck(midi(root), 3.5, 0.3, 500 + k) * 0.5))         # low string on each phrase
            parts.append((t + beat * 3, pluck(midi(root + 7), 3.0, 0.3, 600 + k) * 0.35))
            for m, d in phrase:
                parts.append((t, pluck(midi(m), 2.4, 0.6, k)))
                if d >= 2:  # a sixth below on the long notes, like a second string ringing
                    parts.append((t + 0.03, pluck(midi(m - 9), 2.4, 0.5, 900 + k) * 0.45))
                t += d * beat
                k += 1
    total = t + 2.5
    tt = np.arange(int(total * SR)) / SR
    drone = (np.sin(2 * np.pi * midi(38) * tt) + 0.6 * np.sin(2 * np.pi * midi(45) * tt) + 0.25 * np.sin(2 * np.pi * midi(50) * tt))
    drone = lp(np.tanh(drone), 900) * 0.10 * env(len(tt), 1.5, 2.0)
    parts.append((0.0, drone))
    return reverb(mix(*parts), 0.45)


def allfather():
    """A slow, stately horn call with the war drums keeping time beneath it."""
    parts = []
    beat = 0.75
    calls = [  # (start beat, Hz path, seconds)
        (0, [147, 147, 146], 1.3), (2, [196, 220, 220, 219], 2.0),
        (5, [175, 175], 0.8), (6, [196, 196], 0.8), (7, [220, 220, 220], 2.2),
        (10, [147, 147], 1.0), (11.5, [220, 294, 294, 293], 3.2),
    ]
    for b, fz, d in calls:
        parts.append((b * beat, horn(fz, d, attack=0.15, release=0.7) * 0.85))
        parts.append((b * beat + 0.02, horn([f / 2 for f in fz], d, attack=0.2, release=0.7) * 0.45))  # second horn an octave down
    for i in range(20):
        accent = 1.0 if i % 4 == 0 else 0.55
        parts.append((i * beat, drum(118 if i % 4 == 0 else 136, accent, 200 + i)))
    return reverb(mix(*parts), 0.4)


# ------------------------------------------------------------------ keyboard taps
def rune_key(f0, dur, grit, seed):
    """A tiny stone-on-wood tap for a key press."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 90) + 0.4 * np.sin(2 * np.pi * f0 * 2.3 * t) * np.exp(-t * 140)
    click = bp(rng.standard_normal(n), 1800, 6000) * np.exp(-t * 600) * grit
    return (body + click) * env(n, 0.0005, 0.01)


# ------------------------------------------------------------------ output
def write_ogg(path, x, peak):
    x = norm(x, peak)
    loud = np.nonzero(np.abs(x) > 0.004)[0]
    x = x[: min(len(x), loud[-1] + int(0.05 * SR))] if len(loud) else x
    x = x * env(len(x), 0.002, 0.04)
    st = (np.stack([x, x], 1) * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    import wave
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())
    title = os.path.splitext(os.path.basename(path))[0]
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", tmp, "-c:a", "libvorbis", "-q:a", "6",
                    "-metadata", f"title={title}", "-metadata", "artist=Yggdrasil", path], check=True)
    os.unlink(tmp)
    print(f"{path}: {len(x) / SR:.1f}s")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "phone-sounds"
    for d in ("Ringtones", "Notifications", "Alarms"):
        os.makedirs(os.path.join(out, d), exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    chiptune.render(tmp, plan=[(112, 216, 2)], ending=False)
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", tmp, "-c:a", "libvorbis", "-q:a", "6",
                    "-metadata", "title=Yggdrasil - Mountain King", "-metadata", "artist=Yggdrasil",
                    os.path.join(out, "Ringtones", "Yggdrasil - Mountain King.ogg")], check=True)
    os.unlink(tmp)

    n = os.path.join(out, "Notifications")
    write_ogg(os.path.join(n, "Yggdrasil - Mjolnir.ogg"), mjolnir(), 0.95)
    write_ogg(os.path.join(n, "Yggdrasil - Ravens.ogg"), ravens(), 0.7)
    write_ogg(os.path.join(n, "Yggdrasil - Heimdall.ogg"), heimdall(), 0.85)
    write_ogg(os.path.join(n, "Yggdrasil - War Horn.ogg"), war_horn(), 0.95)
    write_ogg(os.path.join(n, "Yggdrasil - Rune Stone.ogg"), rune_stone(), 0.9)
    write_ogg(os.path.join(n, "Yggdrasil - War Drums.ogg"), war_drums(), 0.95)
    r = os.path.join(out, "Ringtones")
    write_ogg(os.path.join(r, "Yggdrasil - Freyja's Lyre.ogg"), freyja(), 0.9)
    write_ogg(os.path.join(r, "Yggdrasil - Allfather.ogg"), allfather(), 0.95)
    k = os.path.join(out, "Keys")
    os.makedirs(k, exist_ok=True)
    write_ogg(os.path.join(k, "rune_tap.ogg"), rune_key(420, 0.06, 0.8, 1), 0.5)
    write_ogg(os.path.join(k, "rune_space.ogg"), rune_key(300, 0.08, 0.6, 2), 0.5)
    write_ogg(os.path.join(k, "rune_delete.ogg"), rune_key(260, 0.07, 1.0, 3), 0.5)
    write_ogg(os.path.join(k, "rune_enter.ogg"), rune_key(200, 0.11, 0.7, 4), 0.55)
    write_ogg(os.path.join(out, "Alarms", "Yggdrasil - Longship.ogg"), longship(), 0.95)


if __name__ == "__main__":
    main()
