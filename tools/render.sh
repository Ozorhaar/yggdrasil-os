#!/usr/bin/env bash
# Regenerates every binary theme asset into files/system/.
# Needs: python3 (+numpy for sounds), rsvg-convert, ImageMagick, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=files/system
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 tools/art.py "$TMP"

# ---- wallpapers (KDE wallpaper packages)
wall() { # id svg title
  local d="$ROOT/usr/share/wallpapers/Yggdrasil-$1"
  mkdir -p "$d/contents/images"
  rsvg-convert -w 3840 -h 2160 "$TMP/$2" -o "$TMP/$1.png"
  convert "$TMP/$1.png" -quality 92 "$d/contents/images/3840x2160.jpg"
  convert "$TMP/$1.png" -resize 1920x1080 -quality 92 "$d/contents/images/1920x1080.jpg"
  convert "$TMP/$1.png" -resize 600x338 "$d/contents/screenshot.png"
  cat > "$d/metadata.json" <<EOF
{
    "KPlugin": {
        "Authors": [{ "Name": "Yggdrasil OS" }],
        "Id": "Yggdrasil-$1",
        "License": "CC-BY-SA-4.0",
        "Name": "$3"
    }
}
EOF
}
wall Fjord wall-fjord.svg "Yggdrasil – Fjord at Dusk"
wall WorldTree wall-worldtree.svg "Yggdrasil – The World Tree"
wall Iron wall-iron.svg "Yggdrasil – Forged Iron"
# generic background path some tools look for
mkdir -p "$ROOT/usr/share/backgrounds/yggdrasil"
cp "$ROOT/usr/share/wallpapers/Yggdrasil-Fjord/contents/images/3840x2160.jpg" "$ROOT/usr/share/backgrounds/yggdrasil/fjord.jpg"

# ---- logo / icons
for s in 16 22 24 32 48 64 128 256 512; do
  d="$ROOT/usr/share/icons/hicolor/${s}x${s}/apps"; mkdir -p "$d"
  if [ "$s" -le 32 ]; then src=logo-symbolic.svg; else src=logo.svg; fi
  rsvg-convert -w "$s" -h "$s" "$TMP/$src" -o "$d/yggdrasil-logo.png"
done
mkdir -p "$ROOT/usr/share/icons/hicolor/scalable/apps"
cp "$TMP/logo.svg" "$ROOT/usr/share/icons/hicolor/scalable/apps/yggdrasil-logo.svg"
mkdir -p "$ROOT/usr/share/pixmaps"
rsvg-convert -w 256 -h 256 "$TMP/logo.svg" -o "$ROOT/usr/share/pixmaps/yggdrasil-logo.png"

# ---- plymouth boot splash
P="$ROOT/usr/share/plymouth/themes/yggdrasil"; mkdir -p "$P"
rsvg-convert -w 300 -h 300 "$TMP/logo.svg" -o "$P/logo.png"
for i in 0 1 2 3 4 5 6 7 8; do rsvg-convert -h 64 "$TMP/rune$i.svg" -o "$P/rune$i.png"; done
convert -size 300x6 xc:none -fill '#c8a25a' -draw "roundrectangle 0,0 299,5 3,3" "$P/bar.png"
convert -size 300x6 xc:none -fill '#2a2f36' -draw "roundrectangle 0,0 299,5 3,3" "$P/bar-bg.png"
convert -size 14x14 xc:none -fill '#c8a25a' -draw "circle 7,7 7,2" "$P/bullet.png"
convert -size 320x40 xc:'#121b2e' -fill none -stroke '#c8a25a' -strokewidth 2 -draw "roundrectangle 1,1 318,38 6,6" "$P/entry.png"

# ---- KDE splash (look-and-feel) images
S="$ROOT/usr/share/plasma/look-and-feel/org.yggdrasil.desktop/contents/splash/images"; mkdir -p "$S"
rsvg-convert -w 360 -h 360 "$TMP/logo.svg" -o "$S/logo.png"
rsvg-convert -h 60 "$TMP/name-runes.svg" -o "$S/name-runes.png"
PV="$ROOT/usr/share/plasma/look-and-feel/org.yggdrasil.desktop/contents/previews"; mkdir -p "$PV"
cp "$ROOT/usr/share/wallpapers/Yggdrasil-Fjord/contents/screenshot.png" "$PV/preview.png"
cp "$ROOT/usr/share/wallpapers/Yggdrasil-Fjord/contents/screenshot.png" "$PV/fullscreenpreview.jpg"

# ---- sounds
python3 tools/sounds.py "$TMP/snd"
SND="$ROOT/usr/share/sounds/yggdrasil/stereo"; mkdir -p "$SND"
for f in "$TMP"/snd/*.wav; do
  n=$(basename "$f" .wav)
  ffmpeg -loglevel error -y -i "$f" -c:a libvorbis -q:a 5 -f ogg "$SND/$n.oga"
done
echo "assets rendered into $ROOT"
