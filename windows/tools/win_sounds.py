#!/usr/bin/env python3
"""Yggdrasil Windows sound scheme: the desktop and phone synths, written as
16-bit PCM WAV (the only format Windows system sounds accept).

    python3 windows/tools/win_sounds.py OUT_DIR
"""
import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import chiptune  # noqa: E402
import phone_sounds as ps  # noqa: E402
import sounds as ds  # noqa: E402
from sounds import SR, anvil, env, horn, reverb, wood  # noqa: E402


def write(path, x, peak):
    """Normalise, trim trailing silence, short fade, stereo 16-bit 48 kHz."""
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    loud = np.nonzero(np.abs(x) > 0.004)[0]
    x = x[: min(len(x), loud[-1] + int(0.05 * SR))] if len(loud) else x
    x = x * env(len(x), 0.002, 0.04)
    ds.write(path, x, peak)
    print(f"{os.path.basename(path)}: {len(x) / SR:.1f}s")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "win-sounds"
    os.makedirs(out, exist_ok=True)
    p = lambda name: os.path.join(out, f"Yggdrasil - {name}.wav")  # noqa: E731

    # horns (same calls as Yggdrasil OS)
    call = np.concatenate([horn([98, 110, 110, 110], 1.8), np.zeros(int(0.15 * SR)), horn([110, 147, 147, 146], 1.6)])
    write(p("Sign In"), reverb(call, 0.5), 0.7)
    write(p("Sign Out"), reverb(horn([147, 130, 110, 98], 1.6), 0.5), 0.6)
    write(p("Unlock"), reverb(horn([110, 147, 147], 1.0), 0.4), 0.6)
    write(p("Complete"), reverb(horn([147, 147, 196, 196], 0.7), 0.3), 0.5)
    write(p("Low Battery"), reverb(horn([98, 92], 0.9), 0.3), 0.5)
    # anvil strikes for dialogs
    write(p("Warning"), reverb(anvil(620), 0.3), 0.7)
    write(p("Error"), reverb(np.concatenate([anvil(520, 0.25), anvil(520, 1.4)]), 0.3), 0.75)
    write(p("Information"), reverb(anvil(900, 0.9, 0.5), 0.3), 0.45)
    write(p("Beep"), anvil(1300, 0.4, 0.3), 0.35)
    write(p("Failure"), reverb(anvil(440, 1.2), 0.3), 0.6)
    # wooden knocks
    write(p("Device Connect"), np.concatenate([wood(180), wood(240)]), 0.6)
    write(p("Device Disconnect"), np.concatenate([wood(240), wood(180)]), 0.6)
    write(p("Recycle Bin"), np.concatenate([wood(140), wood(120), wood(100)]), 0.55)
    # the phone set
    write(p("Mjolnir"), ps.mjolnir(), 0.95)
    write(p("Ravens"), ps.ravens(), 0.7)
    write(p("Heimdall"), ps.heimdall(), 0.85)
    write(p("War Horn"), ps.war_horn(), 0.95)
    write(p("Rune Stone"), ps.rune_stone(), 0.9)
    write(p("War Drums"), ps.war_drums(), 0.95)
    write(p("Freyja's Lyre"), ps.freyja(), 0.9)
    write(p("Allfather"), ps.allfather(), 0.95)
    write(p("Longship"), ps.longship(), 0.95)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "mk.wav")
        chiptune.render(wav, plan=[(112, 216, 2)], ending=False)
        shutil.copyfile(wav, p("Mountain King"))
        print("Yggdrasil - Mountain King.wav")


if __name__ == "__main__":
    main()
