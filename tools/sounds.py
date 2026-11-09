#!/usr/bin/env python3
"""Synthesises the Yggdrasil sound theme (horn, anvil, wood) from scratch."""
import os
import sys
import wave

import numpy as np

SR = 48000


def env(n, a, r):
    """attack/release envelope in samples."""
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def reverb(x, mix=0.3):
    out = x.copy()
    for d, g in ((0.031, 0.5), (0.047, 0.42), (0.061, 0.36), (0.089, 0.3), (0.113, 0.24)):
        k = int(d * SR)
        y = np.zeros(len(x) + k * 8)
        y[:len(x)] = x
        for i in range(1, 8):
            y[k * i:k * i + len(x)] += x * (g ** i)
        out = np.pad(out, (0, len(y) - len(out)))
        out += y * mix / 5
    return out


def horn(freqs, dur, t_split=None, attack=0.18, release=0.6):
    """Brass-like horn: harmonic stack, gliding pitch, vibrato, breathy noise."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.interp(t, np.linspace(0, dur, len(freqs)), freqs)
    f = f * (1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.6, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    brightness = np.clip(t / 0.35, 0, 1)
    x = np.zeros(n)
    for h in range(1, 12):
        amp = (1 / h ** 1.1) * (brightness ** (h / 4))
        x += amp * np.sin(h * ph)
    x += 0.02 * np.random.default_rng(1).standard_normal(n) * brightness
    x = np.tanh(1.6 * x)
    return x * env(n, attack, min(release, dur))


def anvil(f0=620, dur=1.6, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for ratio, amp, dec in ((1, 1, 2.2), (2.76, 0.6, 3.5), (5.40, 0.4 * bright, 5.5),
                            (8.93, 0.25 * bright, 8), (13.3, 0.12 * bright, 12)):
        x += amp * np.sin(2 * np.pi * f0 * ratio * t) * np.exp(-dec * t)
    click = np.random.default_rng(2).standard_normal(n) * np.exp(-180 * t) * 0.6
    return (x + click) * env(n, 0.001, 0.05)


def wood(f0=180, dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f0 * t) * np.exp(-22 * t) + 0.5 * np.sin(2 * np.pi * f0 * 2.3 * t) * np.exp(-35 * t)
    x += np.random.default_rng(3).standard_normal(n) * np.exp(-120 * t) * 0.3
    return x * env(n, 0.001, 0.03)


def write(path, x, gain=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    st = np.stack([x, x], axis=1)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    # login: the opening of Grieg's "In the Hall of the Mountain King" (1875,
    # public domain) as an 8-bit chiptune -- once sneaky, once flat out, then
    # three stabs. Eleven seconds of square waves sounds far louder than it measures,
    # so it sits a few dB under the short dialog sounds (about -28 dBFS average).
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import chiptune
    chiptune.render(f"{out}/desktop-login.wav", plan=[(160, 195, 1), (210, 250, 4)],
                    sections=[chiptune.SECTION_A], peak=0.17)
    # the old login: a long rising war-horn call, then a second, higher blast
    # (switch back with:  yggdrasil-theme login-sound horn)
    call = np.concatenate([horn([98, 110, 110, 110], 1.8), np.zeros(int(0.15 * SR)),
                           horn([110, 147, 147, 146], 1.6)])
    write(f"{out}/desktop-login-horn.wav", reverb(call, 0.5), 0.135)
    write(f"{out}/desktop-logout.wav", reverb(horn([147, 130, 110, 98], 1.6), 0.5), 0.6)
    write(f"{out}/service-login.wav", reverb(horn([110, 147, 147], 1.0), 0.4), 0.6)
    write(f"{out}/complete.wav", reverb(horn([147, 147, 196, 196], 0.7), 0.3), 0.5)
    write(f"{out}/outcome-success.wav", reverb(horn([147, 196, 196], 0.6), 0.3), 0.5)
    # alerts: anvil strikes
    write(f"{out}/dialog-warning.wav", reverb(anvil(620), 0.3), 0.7)
    write(f"{out}/dialog-error.wav", reverb(np.concatenate([anvil(520, 0.25), anvil(520, 1.4)]), 0.3), 0.75)
    write(f"{out}/dialog-information.wav", reverb(anvil(900, 0.9, 0.5), 0.3), 0.45)
    write(f"{out}/message-new-instant.wav", reverb(anvil(1100, 0.7, 0.4), 0.25), 0.4)
    write(f"{out}/message.wav", reverb(anvil(1100, 0.7, 0.4), 0.25), 0.4)
    write(f"{out}/bell.wav", anvil(1300, 0.4, 0.3), 0.35)
    write(f"{out}/outcome-failure.wav", reverb(anvil(440, 1.2), 0.3), 0.6)
    # devices & small things: wooden knocks
    write(f"{out}/device-added.wav", np.concatenate([wood(180), wood(240)]), 0.6)
    write(f"{out}/device-removed.wav", np.concatenate([wood(240), wood(180)]), 0.6)
    write(f"{out}/power-plug.wav", wood(260), 0.5)
    write(f"{out}/power-unplug.wav", wood(160), 0.5)
    write(f"{out}/trash-empty.wav", np.concatenate([wood(140), wood(120), wood(100)]), 0.55)
    write(f"{out}/battery-low.wav", reverb(horn([98, 92], 0.9), 0.3), 0.5)


if __name__ == "__main__":
    main()
