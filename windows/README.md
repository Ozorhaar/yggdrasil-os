# Yggdrasil for Windows

The Yggdrasil theme for **allfather** (Windows 11 Pro, Odyssey G9 5120×1440).
Per-user only, no admin rights, no theme patchers, nothing injected into Explorer.

| Part | What it is |
|---|---|
| **Yggdrasil Sky** (`sky/`) | The living fjord wallpaper: a port of the launcher's `FjordScene` running in WebView2 behind the desktop icons. Sky follows the real sunrise/sunset and Open-Meteo weather (rain, snow, storms, fog, clouds), with aurora on dark clear nights. Draws ~15 fps for weather and aurora, 5 fps on calm days (drifting clouds, shimmering water); pauses when a window is maximised and suspends for games, full-screen apps, lock and display-off. Plays the sign-in horn (Windows 8+ has no working sign-in sound). Tray menu: demo, pause, refresh weather, quit. |
| Wallpapers | Fjord, World Tree, Iron at 5120×1440 (`theme/Wallpapers`). Fjord is the static fallback under Sky and the lock screen. |
| Sounds | The same files as the phone and Yggdrasil OS (`win_sounds.py` converts them to 16-bit PCM WAV), registered as the "Yggdrasil" sound scheme: Mountain King chiptune at sign-in (played by Sky), Mjolnir (notifications, IM, SMS), Ravens (mail), Rune Stone (reminders), Heimdall (UAC), anvil dialogs, wooden device knocks, Mountain King (Phone Link calls), Longship (alarms). Credits for the recordings in `theme/Sounds/CREDITS.md`. |
| Cursors | All 17 pointer roles, carved gold with a frost edge (`win_cursors.py`), 32 to 128 px in every file; a spinning rune ring for busy, a spear for links. |
| Icons | Shield icons for This PC, your user folder, Network and the Recycle Bin, plus Documents, Downloads, Pictures, Music and Videos. More emblems (Games, Code, Projects, Archive, Folder) for any folder: `Set-FolderIcon.ps1 -Path D:\Games -Icon Games` (or `-Reset`). |
| Widgets | Rainmeter skins: a runic clock and Forge/Fire/Mind/Bifrost meters (CPU, GPU, RAM, network) in carved iron frames, top-right of the G9. Needs Rainmeter (`winget install Rainmeter.Rainmeter`, asks for admin). |
| Colours | Dark mode, gold `#C8A25A` accent, dark taskbar/Start with gold highlights. |
| Terminal | A "Yggdrasil" Windows Terminal profile + colour scheme, added as a fragment (your `settings.json` is untouched), opening with fastfetch and the same tree logo as Yggdrasil OS. fastfetch installs per-user through winget. |
| Font | Yggdrasil Runic, installed for your account only. |

Runes follow the Yggdrasil rule: never sowilo, tiwaz, algiz, othala or jera (`win_art.py` filters them).

## Install

1. Get `Yggdrasil-Windows-<version>.zip` from the `windows` workflow (artifact or `windows-v*` release).
2. Verify it came from this repo's CI:
   `gh attestation verify Yggdrasil-Windows-<version>.zip --repo Ozorhaar/yggdrasil-os`
3. Unzip, then in **Windows PowerShell** (not as admin):
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1`
   The installer checks every file against `SHA256SUMS` before touching anything and backs up your current theme, sounds and colours.
   Options: `-NoSky -NoSounds -NoLockScreen -NoTerminal -NoCursors -NoFolderIcons -NoFastfetch -NoWidgets`.
4. SmartScreen will warn once about `YggdrasilSky.exe` (unsigned; signing costs money).

`Uninstall.ps1` stops Sky, removes everything and restores the backup.

Sky's settings: `%LOCALAPPDATA%\Yggdrasil\Sky\settings.json` (location, `Fps`, `CalmFps`, `RenderScale`, `PauseWhenCovered`, `Weather`, `SignInHorn`, `UnlockHorn`). Log: `sky.log` in the same folder.

## Build

- Assets (Mac mini): `windows/tools/build.sh` — needs python3 + numpy + scipy + Pillow, rsvg-convert, ffmpeg. Commit the output.
- App + package: the `windows` GitHub workflow (actions pinned to commit SHAs, locked NuGet restore, build provenance attestation), or locally on Windows with the .NET 10 SDK: `pwsh windows/tools/package.ps1`.
- After changing NuGet references, run `dotnet restore windows/sky` once and commit `packages.lock.json`; CI restores in locked mode.

Preview the scene in any browser: serve `windows/sky/web/` and open `index.html?at=22:30&aurora=1`, `?at=12:00&code=63` (rain), `?code=95` (storm), `?code=73` (snow), `?code=45` (fog), or `?demo=1`.
