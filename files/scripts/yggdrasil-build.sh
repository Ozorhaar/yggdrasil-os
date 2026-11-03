#!/usr/bin/env bash
# Image-build steps for Yggdrasil OS that need more than copying files.
set -euxo pipefail

chmod 0755 /usr/bin/yggdrasil-theme
fc-cache -f /usr/share/fonts/yggdrasil || true

# ---------------------------------------------------------------- branding
# Only the display name changes; ID/VARIANT stay Bazzite's so its update and
# helper tooling keeps working.
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="Yggdrasil OS"/' /usr/lib/os-release
sed -i 's/^DEFAULT_HOSTNAME=.*/DEFAULT_HOSTNAME="yggdrasil"/' /usr/lib/os-release
grep -q '^DEFAULT_HOSTNAME=' /usr/lib/os-release || echo 'DEFAULT_HOSTNAME="yggdrasil"' >> /usr/lib/os-release

# ---------------------------------------------------------------- system-wide KDE defaults
# Fresh accounts get the colours even before the first-run script fires.
{
    sed '/^\[General\]/,/^$/d' /usr/share/color-schemes/Yggdrasil.colors
    cat <<'EOF'

[General]
ColorScheme=Yggdrasil
AccentColor=200,162,90

[Icons]
Theme=Yggdrasil

[WM]
activeFont=Yggdrasil Runic,11,-1,5,50,0,0,0,0,0

[KDE]
LookAndFeelPackage=org.yggdrasil.desktop

[Sounds]
Enable=true
Theme=yggdrasil
EOF
} > /etc/xdg/kdeglobals

cat > /etc/xdg/ksplashrc <<'EOF'
[KSplash]
Engine=KSplashQML
Theme=org.yggdrasil.desktop
EOF

cat > /etc/xdg/konsolerc <<'EOF'
[Desktop Entry]
DefaultProfile=Yggdrasil.profile
EOF

cat > /etc/xdg/kscreenlockerrc <<'EOF'
[Greeter]
WallpaperPlugin=org.kde.image

[Greeter][Wallpaper][org.kde.image][General]
Image=file:///usr/share/wallpapers/Yggdrasil-Fjord/
EOF

# ---------------------------------------------------------------- login screen
# Plasma Login Manager keeps the Breeze layout but takes our wallpaper.
if command -v kwriteconfig6 >/dev/null; then
    kwriteconfig6 --file /etc/plasmalogin.conf --group Greeter --key WallpaperPluginId org.kde.image
    kwriteconfig6 --file /etc/plasmalogin.conf --group Greeter --group Wallpaper --group org.kde.image \
        --group General --key Image "file:///usr/share/wallpapers/Yggdrasil-Fjord/contents/images/3840x2160.jpg"
fi
# If the base image is still on SDDM, theme its Breeze greeter instead.
if [ -d /usr/share/sddm/themes/breeze ]; then
    cat > /usr/share/sddm/themes/breeze/theme.conf.user <<'EOF'
[General]
background=/usr/share/wallpapers/Yggdrasil-Fjord/contents/images/3840x2160.jpg
type=image
EOF
fi

# ---------------------------------------------------------------- icons: Papirus with oak-brown folders
if [ -d /usr/share/icons/Papirus-Dark ]; then
    curl -fsSL -o /tmp/papirus-folders \
        https://raw.githubusercontent.com/PapirusDevelopmentTeam/papirus-folders/master/papirus-folders
    chmod +x /tmp/papirus-folders
    /tmp/papirus-folders -C brown --theme Papirus-Dark || true
    rm -f /tmp/papirus-folders
fi

# ---------------------------------------------------------------- Norse app names
# Name= becomes the Norse name; the original stays as the description and as a
# search keyword, so searching "steam" or "terminal" still finds them.
rename_app() { # file newname
    local f="/usr/share/applications/$1"
    [ -f "$f" ] || return 0
    local old
    old=$(grep -m1 '^Name=' "$f" | cut -d= -f2-)
    sed -i "0,/^Name=.*/s//Name=$2/" "$f"
    sed -i '/^Name\[en/d' "$f"
    grep -q '^GenericName=' "$f" || sed -i "0,/^Name=.*/s//&\nGenericName=$old/" "$f"
    if grep -q '^Keywords=' "$f"; then
        sed -i "0,/^Keywords=/s//Keywords=$old;/" "$f"
    else
        echo "Keywords=$old;" >> "$f"
    fi
}
rename_app steam.desktop "Valhalla (Steam)"
rename_app org.kde.konsole.desktop "Rune Console"
rename_app org.kde.dolphin.desktop "The Hoard"
rename_app systemsettings.desktop "The Forge"
rename_app org.kde.plasma-systemmonitor.desktop "Heimdall"
rename_app io.github.kolunmi.Bazaar.desktop "Trading Post"

# ---------------------------------------------------------------- boot splash
plymouth-set-default-theme yggdrasil

# Rebuild the initramfs so the new splash is actually inside it (same dracut
# invocation the Bazzite image uses).
KVER=$(ls /usr/lib/modules | sort -V | tail -n1)
/usr/bin/dracut --no-hostonly --kver "$KVER" --reproducible --zstd -v \
    --add ostree --add fido2 -f "/usr/lib/modules/$KVER/initramfs.img"
chmod 0600 "/usr/lib/modules/$KVER/initramfs.img"
