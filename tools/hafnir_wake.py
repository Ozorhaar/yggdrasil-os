#!/usr/bin/env python3
"""Hafnir's own wake sounds, synthesised like the rest of the Yggdrasil set (nothing sampled).

    python3 tools/hafnir_wake.py OUTDIR

Writes OUTDIR/Hafnir/*.ogg. Each is short (well under a second) so Hafnir starts
listening at once and the sound doesn't spill into what you say.
  Hafnir - Horn Clink.ogg   two drinking horns raised and knocked together, ringing: skal, I'm listening
                            (the default wake sound in the Hafnir app, res/raw/hafnir_horn_clink.ogg)
  Hafnir - Call.ogg         a short, warm two-note horn rising a fifth (higher and brighter than Heimdall)
  Hafnir - Ember Rune.ogg   a struck rune stone with a warm hum swelling under it
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from phone_sounds import bp, hp, lp, mix, norm, silence, stone_tap, write_ogg  # noqa: E402
from sounds import SR, env, horn, reverb  # noqa: E402


def horn_knock(f0, seed, dur=0.30, ring=1.0):
    """A drinking horn struck against another: hollow, woody-bony, a short ring.
    ring > 1 lets the horn sing on longer after the knock."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    modes = ((1.0, 1.0, 38 / ring), (1.58, 0.65, 52 / ring), (2.37, 0.40, 70 / ring), (3.61, 0.22, 95 / ring))
    body = sum(a * np.sin(2 * np.pi * f0 * r * t + rng.uniform(0, 6)) * np.exp(-d * t) for r, a, d in modes)
    hollow = bp(rng.standard_normal(n), f0 * 0.7, f0 * 1.8) * np.exp(-55 * t) * 0.9
    click = hp(rng.standard_normal(n), 2500) * np.exp(-900 * t) * 0.5
    return (body + hollow + click) * env(n, 0.0005, 0.04)


def horn_clink(gap=0.16, ring=2.0, dur=0.55, room=0.36):
    a = norm(horn_knock(880, 3, dur, ring), 1.0)
    b = norm(horn_knock(1040, 4, dur, ring), 0.85)
    x = mix((0.0, a), (gap, b))
    return reverb(np.tanh(1.6 * x), room)


def call():
    low = horn([196, 200, 200], 0.20, attack=0.035, release=0.06)
    high = horn([290, 296, 296, 294], 0.34, attack=0.03, release=0.18)
    x = np.concatenate([low, silence(0.03), high])
    x = np.tanh(1.4 * x) + 0.25 * hp(x, 700)
    return reverb(x, 0.35)


def ember_rune():
    tap = norm(stone_tap(700, 5)[: int(0.25 * SR)], 1.0)
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = np.interp(t, [0, 0.55], [220, 330])
    hum = sum(a * np.sin(2 * np.pi * np.cumsum(f * h) / SR) for h, a in ((1, 1), (2, 0.35), (3, 0.12)))
    hum = lp(hum, 1800) * env(n, 0.12, 0.25) * 0.45
    x = mix((0.0, tap), (0.04, hum))
    return reverb(np.tanh(1.3 * x), 0.4)


def main():
    out = os.path.join(sys.argv[1] if len(sys.argv) > 1 else "phone-sounds", "Hafnir")
    os.makedirs(out, exist_ok=True)
    write_ogg(os.path.join(out, "Hafnir - Horn Clink.ogg"), horn_clink(), 0.9)
    write_ogg(os.path.join(out, "Hafnir - Call.ogg"), call(), 0.9)
    write_ogg(os.path.join(out, "Hafnir - Ember Rune.ogg"), ember_rune(), 0.9)


if __name__ == "__main__":
    main()
