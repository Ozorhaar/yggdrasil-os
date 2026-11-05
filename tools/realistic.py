#!/usr/bin/env python3
"""The realistic Yggdrasil phone sounds, cut and mixed from real recordings (Freesound).

    ~/.venvs/ygg-sounds/bin/python tools/realistic.py OUTDIR [name ...]

Recordings are fetched once into ~/.cache/yggdrasil-sounds/ (needs the Freesound key, see
freesound.py) and every source is listed in SOURCES, which also writes OUTDIR/CREDITS.md.
All CC0 unless noted. Personal use. The synthesised originals stay in phone_sounds.py.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.ndimage import maximum_filter1d
from scipy.signal import butter, resample_poly, sosfilt

sys.path.insert(0, os.path.dirname(__file__))
from phone_sounds import FFMPEG  # noqa: E402

SR = 48000
CACHE = os.path.expanduser("~/.cache/yggdrasil-sounds")

# freesound id -> what it is (credits come from the API on first fetch)
SOURCES = {
    835819: "two mugs knocked together (Hafnir's Horn Clink)",
    386102: "hammer on the horn of a 100 kg anvil (Mjolnir)",
    38245: "thunder crack and roll (Mjolnir)",
    275466: "raven calls (Ravens)",
    512781: "a raven call (Ravens)",
    328541: "a deep horn, one long blow (War Horn)",
    392180: "a battle horn, one long blow (Heimdall)",
    703007: "a handful of dice thrown into a tray (Rune Stone: casting the bones)",
    85781: "a big native hide drum, struck once (War Drums)",
}


# ------------------------------------------------------------------ plumbing
def fetch(sid):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{sid}.ogg")
    meta = os.path.join(CACHE, f"{sid}.json")
    if not os.path.exists(path):
        out = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "freesound.py"), "get", str(sid), path],
                             capture_output=True, text=True, check=True).stdout
        open(meta, "w").write(out.strip().splitlines()[-1])
    return path


def load(sid):
    raw = subprocess.run([FFMPEG, "-loglevel", "error", "-i", fetch(sid), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return x - x.mean()


def hits(x, thresh_db=-24, jump_db=9, min_gap=0.06):
    hop = int(0.005 * SR)
    fr = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(fr / (fr.max() + 1e-12) + 1e-9)
    rise = np.diff(db, prepend=-120.0)          # a sound that starts loud counts as a hit at 0
    out, last = [], -10**9
    for i in range(len(db)):
        if db[i] > thresh_db and rise[i] > jump_db and (i - last) * hop > min_gap * SR:
            out.append(i * hop / SR)
            last = i
    if not out:                                  # soft swells: take where it first gets near its peak
        out = [int(np.argmax(db > -6)) * hop / SR]
    return out


def cut(x, t0, dur, pre=0.006):
    s = max(0, int((t0 - pre) * SR))
    return x[s:s + int(dur * SR)].copy()


def fade(x, fin=0.003, fout=0.15, curve=2.0):
    x = x.copy()
    a, b = int(fin * SR), min(int(fout * SR), len(x) // 2)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b) ** curve
    return x


def pitch(x, semis):
    """Tape-style pitch change (also changes length slightly)."""
    r = 2 ** (semis / 12)
    up, down = int(round(1000)), int(round(1000 * r))
    return resample_poly(x, up, down)


def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-12) * peak


def lp(x, hz):
    return sosfilt(butter(4, hz, "low", fs=SR, output="sos"), x)


def hp(x, hz):
    return sosfilt(butter(2, hz, "high", fs=SR, output="sos"), x)


def mix(*parts):
    end = max(int(o * SR) + len(p) for o, p in parts)
    out = np.zeros(end)
    for o, p in parts:
        s = int(o * SR)
        out[s:s + len(p)] += p
    return out


def phone_bass(x, amount=0.7):
    """Phone speakers can't play much below ~150-200 Hz. Add harmonics of the low end
    (150-600 Hz) so the ear hears the boom anyway ("missing fundamental")."""
    low = lp(x, 150)
    h = sosfilt(butter(2, [150, 600], "band", fs=SR, output="sos"), np.tanh(4 * low / (np.abs(low).max() + 1e-12)))
    y = x / (np.abs(x).max() + 1e-12) + amount * h / (np.abs(h).max() + 1e-12) * 0.6
    # what a phone can't play only eats loudness: drop it below ~90 Hz
    return sosfilt(butter(4, 90, "high", fs=SR, output="sos"), y)


def limit(x, ceiling_db=-12.0, look=0.004, release=0.08):
    """Look-ahead peak limiter: gain never lets |x| exceed the ceiling (relative to the peak),
    reaches its target before the spike arrives and recovers smoothly afterwards."""
    x = x / (np.abs(x).max() + 1e-12)
    c = 10 ** (ceiling_db / 20)
    n = int(look * SR)
    pk = maximum_filter1d(np.abs(x), size=2 * n + 1)          # peak over the look-ahead window
    g = np.minimum(1.0, c / (pk + 1e-12))
    a = np.exp(-1 / (release * SR))
    out = np.empty_like(g); prev = 1.0
    for i, v in enumerate(g):                                   # instant attack, smooth release
        prev = v if v < prev else a * prev + (1 - a) * v
        out[i] = prev
    k = np.ones(n) / n                                          # smooth the gain to avoid clicks
    out = np.minimum(out, np.convolve(out, k, "same"))
    return x * out


def room(x, wet=0.18, size=0.06):
    """A little stone-hall air: a few soft early reflections."""
    out = x.copy()
    for i, (d, g) in enumerate(((size, 0.5), (size * 1.7, 0.35), (size * 2.6, 0.25), (size * 4.1, 0.15))):
        k = int(d * SR)
        refl = np.zeros_like(x)
        refl[k:] = lp(x, 5000 - i * 900)[:-k] if k else x
        out += wet * g * refl
    return out


def write(path, x, peak=0.9):
    x = norm(x, peak)
    st = (np.stack([x, x], 1) * 32767).astype(np.int16)
    title = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "libvorbis", "-q:a", "6", "-metadata", f"title={title}", "-metadata", "artist=Yggdrasil", path],
                   input=st.tobytes(), check=True)
    print(f"{os.path.relpath(path)}: {len(x) / SR:.2f}s")


# ------------------------------------------------------------------ the sounds
def mjolnir():
    """The hammer strikes the anvil, it rings, and thunder answers."""
    anvil = load(386102)
    a = fade(cut(anvil, hits(anvil)[0], 1.4), fout=0.6)
    th = load(38245)
    t0 = hits(th, thresh_db=-20, jump_db=6)[0]
    thunder = fade(cut(th, t0, 2.4, pre=0.02), fout=1.2)
    # shave the strike's spike so the ring and the thunder come up to the other sounds' level
    return limit(mix((0.0, norm(a, 1.0)), (0.12, norm(lp(thunder, 6000), 0.85))), -12)


def ravens():
    """Huginn and Muninn: two calls, the second lower and further off."""
    r = load(275466)
    h = hits(r, thresh_db=-18)
    first = fade(cut(r, h[0], 0.45), fout=0.12)
    r2 = load(512781)
    second = fade(cut(r2, hits(r2)[0], 0.5), fout=0.15)
    second = room(lp(pitch(second, -1.5), 4500), wet=0.35, size=0.05)
    # the recordings carry low rumble a phone cannot play; drop it so the calls come through louder
    return hp(hp(mix((0.0, norm(first, 1.0)), (0.55, norm(second, 0.6))), 180), 180)


def war_horn():
    """One long blow on a deep horn: call to arms."""
    x = load(328541)
    t0 = hits(x, thresh_db=-30, jump_db=5)[0]
    return room(phone_bass(fade(cut(x, t0, 2.4, pre=0.03), fin=0.04, fout=0.8), 0.5), wet=0.25, size=0.09)


def heimdall():
    """The watchman's horn at the bridge: one long blow on a battle horn."""
    x = load(392180)
    t0 = hits(x, thresh_db=-30, jump_db=5)[0]
    return room(fade(cut(x, t0, 2.2, pre=0.03), fin=0.03, fout=0.8), wet=0.3, size=0.12)


def rune_stone():
    """Casting the bones: a handful tumbling into a tray, pitched down for heavier pieces."""
    y = load(703007)
    x = fade(cut(y, hits(y)[0], 1.15), fout=0.45)
    return limit(room(lp(pitch(x, -3), 9000), wet=0.22, size=0.04), -12)


def war_drums():
    """bum . bum-bum . bum on a big hide drum, its boom turned into harmonics a phone can play,
    a little hand-slap on each strike, then compressed so the ring stays up between hits."""
    nd = load(85781)
    t0 = hits(nd)[0]
    short = fade(cut(nd, t0, 0.3), fout=0.1)
    long_ = fade(cut(nd, t0, 1.4), fout=0.7)
    times, gains = (0.0, 0.55, 0.74, 1.12), (0.95, 0.75, 0.8, 1.0)
    dry = mix(*[(t, norm(short, g)) for t, g in zip(times[:-1], gains[:-1])], (times[-1], norm(long_, gains[-1])))
    body = phone_bass(dry, 1.6)
    edge = sosfilt(butter(2, [700, 2500], "band", fs=SR, output="sos"), np.tanh(8 * norm(dry)))
    k = int(0.004 * SR)
    env = np.convolve(np.abs(dry), np.ones(k) / k, "same")
    edge = edge * (env / (env.max() + 1e-12)) ** 1.5
    y = sosfilt(butter(4, 120, "high", fs=SR, output="sos"), norm(body) + 0.45 * norm(edge))
    y = np.tanh(3.6 * norm(y)) / np.tanh(3.6)
    return room(y, wet=0.15, size=0.1)


SOUNDS = {
    "Notifications/Yggdrasil - Mjolnir.ogg": (mjolnir, 0.95),
    "Notifications/Yggdrasil - Ravens.ogg": (ravens, 0.75),
    "Notifications/Yggdrasil - Heimdall.ogg": (heimdall, 0.9),
    "Notifications/Yggdrasil - War Horn.ogg": (war_horn, 0.95),
    "Notifications/Yggdrasil - Rune Stone.ogg": (rune_stone, 0.9),
    "Notifications/Yggdrasil - War Drums.ogg": (war_drums, 0.93),
}


def credits(out):
    lines = ["# Credits for the realistic Yggdrasil sounds", "",
             "Cut and mixed from these Freesound recordings (personal use):", ""]
    for sid, what in SOURCES.items():
        fetch(sid)  # every source must be credited; fetch its metadata if it isn't cached
        m = json.load(open(os.path.join(CACHE, f"{sid}.json")))
        lines.append(f'- {what}: "{m["name"]}" by {m["user"]}, {m["license"]}, {m["url"]}')
    open(os.path.join(out, "CREDITS.md"), "w").write("\n".join(lines) + "\n")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "phone-sounds"
    want = sys.argv[2:]
    for name, (fn, peak) in SOUNDS.items():
        if want and not any(w.lower() in name.lower() for w in want):
            continue
        write(os.path.join(out, name), fn(), peak)
    credits(out)


if __name__ == "__main__":
    main()
