#!/usr/bin/env python3
"""Cut a real recording down to a phone sound: find the first hits, trim, fade, level, write .ogg.

    take.py IN OUT.ogg [--max 0.6] [--hits 2] [--start SECONDS] [--peak 0.9] [--gain-db 0]

--hits N keeps the first N distinct hits (if they fall inside --max); --start skips ahead first.
Uses ffmpeg-full (libvorbis) like phone_sounds.py.
"""
import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from phone_sounds import FFMPEG  # noqa: E402

SR = 48000


def load(path):
    raw = subprocess.run([FFMPEG, "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def onsets(x, min_gap=0.06):
    """Sample positions where the level jumps: hits."""
    hop = int(0.005 * SR)
    frames = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    if frames.max() <= 0:
        return []
    db = 20 * np.log10(frames / frames.max() + 1e-9)
    rise = np.diff(db, prepend=db[0])
    out, last = [], -10**9
    for i, (lvl, r) in enumerate(zip(db, rise)):
        if lvl > -24 and r > 9 and (i - last) * hop > min_gap * SR:
            out.append(i * hop)
            last = i
    return out


def write_ogg(path, x, peak):
    x = x / (np.abs(x).max() + 1e-12) * peak
    st = (np.stack([x, x], 1) * 32767).astype(np.int16)
    title = os.path.splitext(os.path.basename(path))[0]
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "libvorbis", "-q:a", "6", "-metadata", f"title={title}", "-metadata", "artist=Yggdrasil", path],
                   input=st.tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--max", type=float, default=0.6)
    ap.add_argument("--hits", type=int, default=2)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--peak", type=float, default=0.9)
    a = ap.parse_args()

    x = load(a.inp)[int(a.start * SR):]
    x = x - np.mean(x)
    hits = onsets(x)
    if not hits:
        sys.exit("no hits found")
    s = max(0, hits[0] - int(0.008 * SR))
    end = s + int(a.max * SR)
    kept = [h for h in hits if h < end][: a.hits]
    # stop just before the next hit we aren't keeping, or at --max
    later = [h for h in hits if h > kept[-1] and h < end]
    if later:
        end = later[0] - int(0.01 * SR)
    seg = x[s:end].copy()
    n = len(seg)
    fade = min(int(0.12 * SR), n // 3)
    seg[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    seg[-fade:] *= np.linspace(1, 0, fade) ** 2
    write_ogg(a.out, seg, a.peak)
    print(f"{os.path.basename(a.out)}: {n / SR:.2f}s, hits kept {len(kept)} of {len(hits)} found")


if __name__ == "__main__":
    main()
