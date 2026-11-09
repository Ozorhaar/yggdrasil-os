#!/bin/sh
# Copies Yggdrasil Sky's scene (windows/sky/web) into the Plasma wallpaper, so Yggdrasil OS and
# Windows draw the same living fjord. Run after changing the scene; CI checks the copies match.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$ROOT/windows/sky/web"
DST="$ROOT/files/system/usr/share/plasma/wallpapers/org.yggdrasil.livingfjord/contents/web"
mkdir -p "$DST"
for f in kde.html scene.js sky-land.png sky-ship.png; do cp "$SRC/$f" "$DST/$f"; done
echo "synced $(ls "$DST" | wc -l | tr -d ' ') files into the Plasma wallpaper"
