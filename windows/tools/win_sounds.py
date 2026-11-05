#!/usr/bin/env python3
"""Yggdrasil Windows sound scheme: the very same sounds as the phone and the laptop,
converted to 16-bit PCM WAV (the only format Windows system sounds accept).

    python3 windows/tools/win_sounds.py OUT_DIR

Sources (already built and committed by their own tools):
  phone-sounds/   real-recording notifications, ringtones and alarm (phone)
  files/system/usr/share/sounds/yggdrasil/stereo/   desktop event sounds (Yggdrasil OS)
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PHONE = os.path.join(ROOT, "phone-sounds")
LAPTOP = os.path.join(ROOT, "files", "system", "usr", "share", "sounds", "yggdrasil", "stereo")
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")

# Windows name -> source file
SOUNDS = {
    # Yggdrasil OS desktop sounds (same events on both computers)
    "Sign In": f"{LAPTOP}/desktop-login.oga",             # Mountain King chiptune, as on the laptop
    "Unlock": f"{LAPTOP}/service-login.oga",
    "Warning": f"{LAPTOP}/dialog-warning.oga",
    "Error": f"{LAPTOP}/dialog-error.oga",
    "Information": f"{LAPTOP}/dialog-information.oga",
    "Beep": f"{LAPTOP}/bell.oga",
    "Failure": f"{LAPTOP}/outcome-failure.oga",
    "Complete": f"{LAPTOP}/complete.oga",
    "Low Battery": f"{LAPTOP}/battery-low.oga",
    "Device Connect": f"{LAPTOP}/device-added.oga",
    "Device Disconnect": f"{LAPTOP}/device-removed.oga",
    "Recycle Bin": f"{LAPTOP}/trash-empty.oga",
    # phone notifications, ringtones and alarm (real recordings)
    "Mjolnir": f"{PHONE}/Notifications/Yggdrasil - Mjolnir.ogg",
    "Ravens": f"{PHONE}/Notifications/Yggdrasil - Ravens.ogg",
    "Heimdall": f"{PHONE}/Notifications/Yggdrasil - Heimdall.ogg",
    "Rune Stone": f"{PHONE}/Notifications/Yggdrasil - Rune Stone.ogg",
    "War Drums": f"{PHONE}/Notifications/Yggdrasil - War Drums.ogg",
    "War Horn": f"{PHONE}/Notifications/Yggdrasil - War Horn.ogg",
    "Mountain King": f"{PHONE}/Ringtones/Yggdrasil - Mountain King.ogg",
    "Allfather": f"{PHONE}/Ringtones/Yggdrasil - Allfather.ogg",
    "Freyja's Lyre": f"{PHONE}/Ringtones/Yggdrasil - Freyja's Lyre.ogg",
    "Longship": f"{PHONE}/Alarms/Yggdrasil - Longship.ogg",
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "win-sounds"
    os.makedirs(out, exist_ok=True)
    for name, src in SOUNDS.items():
        if not os.path.exists(src):
            sys.exit(f"missing source sound: {src}")
        dst = os.path.join(out, f"Yggdrasil - {name}.wav")
        subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", src, "-map_metadata", "-1",
                        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", dst], check=True)
        print(os.path.basename(dst))
    # The recordings' licences (one is CC-BY) travel with the sounds.
    shutil.copyfile(os.path.join(PHONE, "CREDITS.md"), os.path.join(out, "CREDITS.md"))


if __name__ == "__main__":
    main()
