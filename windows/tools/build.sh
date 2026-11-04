#!/usr/bin/env bash
# Renders every Yggdrasil Windows asset into windows/theme/ and windows/sky/.
# Run on the Mac mini (or any Unix box) after changing art or sounds; commit the result.
# Needs: python3 + numpy + scipy + Pillow, rsvg-convert, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")/../.."
W=${W:-5120}; H=${H:-1440}           # Odyssey G9
T=windows/theme
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

python3 windows/tools/win_art.py "$TMP" "$W" "$H"

# ---- wallpapers + lock screen
mkdir -p "$T/Wallpapers"
for n in Fjord WorldTree Iron; do
  svg="$TMP/wall-$(echo "$n" | tr '[:upper:]' '[:lower:]').svg"
  rsvg-convert -w "$W" -h "$H" "$svg" -o "$TMP/$n.png"
  ffmpeg -loglevel error -y -i "$TMP/$n.png" -q:v 2 "$T/Wallpapers/Yggdrasil - $n.jpg"
done
cp "$T/Wallpapers/Yggdrasil - Fjord.jpg" "$T/LockScreen.jpg"

# ---- living wallpaper layers (transparent PNG)
for n in land ship; do rsvg-convert -w "$W" -h "$H" "$TMP/sky-$n.svg" -o "windows/sky/web/sky-$n.png"; done

# ---- app / folder icon
mkdir -p windows/sky/assets
for s in 16 20 24 32 40 48 64 128 256; do rsvg-convert -w "$s" -h "$s" "$TMP/logo.svg" -o "$TMP/logo-$s.png"; done
python3 - "$TMP" windows/sky/assets/yggdrasil.ico <<'EOF'
import sys
from PIL import Image
tmp, out = sys.argv[1], sys.argv[2]
sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
big = Image.open(f"{tmp}/logo-256.png").convert("RGBA")
big.save(out, sizes=[(s, s) for s in sizes],
         append_images=[Image.open(f"{tmp}/logo-{s}.png").convert("RGBA") for s in sizes[:-1]])
EOF
cp windows/sky/assets/yggdrasil.ico "$T/yggdrasil.ico"

# ---- sounds
rm -rf "$T/Sounds"; python3 windows/tools/win_sounds.py "$T/Sounds"

# ---- font (shared with Yggdrasil OS)
mkdir -p "$T/Fonts"
cp files/system/usr/share/fonts/yggdrasil/YggdrasilRunic.ttf "$T/Fonts/"

echo "Yggdrasil Windows assets rendered into $T and windows/sky/web"
