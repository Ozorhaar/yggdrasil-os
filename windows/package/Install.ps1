#Requires -Version 5.1
<#
.SYNOPSIS
  Installs Yggdrasil for Windows 11 for the current user only. No admin rights.

.DESCRIPTION
  Run from the unzipped folder in Windows PowerShell:
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1
  (-ExecutionPolicy Bypass applies to this one process only.)

  What it does, all under your user account:
    1. Checks every file against SHA256SUMS and stops on any mismatch.
    2. Backs up your current theme, sound scheme and related settings (Uninstall.ps1 restores them).
    3. Copies the theme to %LOCALAPPDATA%\Yggdrasil\Theme and Yggdrasil Sky to
       %LOCALAPPDATA%\Programs\YggdrasilSky.
    4. Registers the "Yggdrasil" sound scheme, the Yggdrasil Runic font, the lock-screen image
       and a Windows Terminal profile + colour scheme (as a fragment; your settings.json is untouched).
    5. Writes Yggdrasil.theme (dark mode, gold accent, Fjord wallpaper, sounds) and applies it.
    6. Starts Yggdrasil Sky and adds it to sign-in (HKCU Run).
  Nothing patches Windows files, injects into Explorer or needs elevation.

.PARAMETER NoSky        Skip the living wallpaper.
.PARAMETER NoSounds     Skip the sound scheme.
.PARAMETER NoLockScreen Leave the lock screen alone.
.PARAMETER NoTerminal   Skip the Windows Terminal profile.
.PARAMETER NoCursors    Keep your current mouse pointers.
.PARAMETER NoFolderIcons Leave Documents, Downloads, Pictures, Music and Videos with their usual icons.
.PARAMETER NoFastfetch  Don't install fastfetch (winget, your account only) for the Terminal banner.
.PARAMETER NoWidgets    Skip the Rainmeter clock and meters.
#>
[CmdletBinding()]
param([switch]$NoSky, [switch]$NoSounds, [switch]$NoLockScreen, [switch]$NoTerminal, [switch]$NoCursors, [switch]$NoFolderIcons, [switch]$NoFastfetch, [switch]$NoWidgets)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Src = $PSScriptRoot

function Say($msg, $color = 'DarkYellow') { Write-Host "  ᚨ $msg" -ForegroundColor $color }
# Creates a registry key only if missing (New-Item -Force would wipe an existing key's values).
function Ensure-Key($path) { if (-not (Test-Path -LiteralPath $path)) { New-Item -Path $path -Force | Out-Null } }

# --------------------------------------------------------------------- 0. refuse admin
$me = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if ($me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "This window is running as Administrator. Open a normal Terminal (not 'Run as administrator') and run Install.ps1 again: everything installs for your account only."
}
if ([Environment]::OSVersion.Version.Build -lt 22000) { throw "Yggdrasil for Windows needs Windows 11." }

# --------------------------------------------------------------------- 1. integrity
Say "Checking files against SHA256SUMS"
$sums = Join-Path $Src 'SHA256SUMS'
if (-not (Test-Path $sums)) { throw "SHA256SUMS is missing; refusing to install." }
$listed = @{}
foreach ($line in Get-Content -LiteralPath $sums -Encoding UTF8) {
    if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { continue }
    $hash, $rel = $Matches[1], $Matches[2]
    if ($rel -match '(^|[\\/])\.\.([\\/]|$)' -or [IO.Path]::IsPathRooted($rel)) { throw "Bad path in SHA256SUMS: $rel" }
    $file = Join-Path $Src $rel
    if (-not (Test-Path -LiteralPath $file)) { throw "Missing file: $rel" }
    $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $hash) { throw "Checksum mismatch: $rel" }
    $listed[$rel.Replace('\', '/')] = $true
}
# every shipped file must be listed (except the list itself)
Get-ChildItem -LiteralPath $Src -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Src.Length + 1).Replace('\', '/')
    if ($rel -ne 'SHA256SUMS' -and -not $listed.ContainsKey($rel)) { throw "Unlisted file in package: $rel" }
}
Say "All $($listed.Count) files match" 'DarkGreen'

# --------------------------------------------------------------------- paths
$Root     = Join-Path $env:LOCALAPPDATA 'Yggdrasil'
$Theme    = Join-Path $Root 'Theme'
$Backup   = Join-Path $Root 'Backup'
$SkyDir   = Join-Path $env:LOCALAPPDATA 'Programs\YggdrasilSky'
$Sounds   = Join-Path $Theme 'Sounds'
$Wall     = Join-Path $Theme 'Wallpapers\Yggdrasil - Fjord.jpg'
New-Item -ItemType Directory -Force -Path $Root, $Backup | Out-Null

# If anything below fails after Sky was stopped, start it again rather than leaving the desktop static.
$SkyExe = Join-Path $SkyDir 'YggdrasilSky.exe'
trap {
    # (Get-Variable: this also catches errors raised before $SkyExe exists, e.g. the admin check)
    $exe = Get-Variable -Name SkyExe -ValueOnly -ErrorAction SilentlyContinue
    if (-not $NoSky -and $exe -and (Test-Path -LiteralPath $exe) -and -not (Get-Process YggdrasilSky -ErrorAction SilentlyContinue)) {
        Start-Process -FilePath $exe
    }
    break
}

# --------------------------------------------------------------------- 2. backup
# Each item is saved the first time any version of the installer is about to change it,
# so the backup always holds your settings from before Yggdrasil.
$keys = [ordered]@{
    'AppEvents'   = 'HKCU\AppEvents\Schemes'
    'Desktop'     = 'HKCU\Control Panel\Desktop'
    'Cursors'     = 'HKCU\Control Panel\Cursors'
    'Personalize' = 'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
    'DWM'         = 'HKCU\Software\Microsoft\Windows\DWM'
    'Accent'      = 'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent'
    'DesktopIcons'= 'HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\CLSID'
}
foreach ($k in $keys.GetEnumerator()) {
    $file = Join-Path $Backup "$($k.Key).reg"
    if (Test-Path -LiteralPath $file) { continue }
    Say "Backing up $($k.Key) settings to $Backup"
    # Start-Process: reg.exe writes to stderr, which PowerShell 5.1 would treat as an error
    Start-Process reg.exe -ArgumentList 'export', "`"$($k.Value)`"", "`"$file`"", '/y' -Wait -WindowStyle Hidden
    if (-not (Test-Path -LiteralPath $file)) { Set-Content -LiteralPath $file -Value 'Windows Registry Editor Version 5.00' -Encoding Unicode }  # key didn't exist
}
$curFile = Join-Path $Backup 'CurrentTheme.txt'
if (-not (Test-Path -LiteralPath $curFile)) {
    $cur = Get-ItemPropertyValue 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes' -Name CurrentTheme -ErrorAction SilentlyContinue
    if ($cur) { Set-Content -LiteralPath $curFile -Value $cur -Encoding UTF8 }
}
Set-Content -LiteralPath (Join-Path $Backup 'done') -Value (Get-Date -Format o)

# --------------------------------------------------------------------- 3. copy files
Say "Copying the theme"
Stop-Process -Name YggdrasilSky -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
New-Item -ItemType Directory -Force -Path $Theme | Out-Null
Copy-Item -Path (Join-Path $Src 'theme\*') -Destination $Theme -Recurse -Force
if (-not $NoSky) {
    New-Item -ItemType Directory -Force -Path $SkyDir | Out-Null
    Copy-Item -Path (Join-Path $Src 'sky\*') -Destination $SkyDir -Recurse -Force
}

# --------------------------------------------------------------------- 4a. sound scheme
if (-not $NoSounds) {
    Say "Registering the Yggdrasil sound scheme"
    # event -> sound (app '.Default' unless noted)
    $map = [ordered]@{
        '.Default'                  = 'Beep'
        'SystemAsterisk'            = 'Information'
        'SystemExclamation'         = 'Warning'
        'SystemHand'                = 'Error'
        'SystemNotification'        = 'Rune Stone'
        'WindowsUAC'                = 'Heimdall'
        'Notification.Default'      = 'Mjolnir'
        'Notification.IM'           = 'Mjolnir'
        'Notification.SMS'          = 'Mjolnir'
        'Notification.Mail'         = 'Ravens'
        'MailBeep'                  = 'Ravens'
        'Notification.Reminder'     = 'Rune Stone'
        'Notification.Looping.Call' = 'Mountain King'
        'Notification.Looping.Alarm'= 'Longship'
        'DeviceConnect'             = 'Device Connect'
        'DeviceDisconnect'          = 'Device Disconnect'
        'DeviceFail'                = 'Failure'
        'AppGPFault'                = 'Error'
        'LowBatteryAlarm'           = 'Low Battery'
        'CriticalBatteryAlarm'      = 'War Horn'
        'PrintComplete'             = 'Complete'
        'ChangeTheme'               = 'Complete'
        'Explorer/EmptyRecycleBin'  = 'Recycle Bin'
        'Explorer/BlockedPopup'     = 'Beep'
        'Explorer/SecurityBand'     = 'Beep'
    }
    $base = 'HKCU:\AppEvents\Schemes'
    Ensure-Key "$base\Names\Yggdrasil"
    Set-ItemProperty -Path "$base\Names\Yggdrasil" -Name '(default)' -Value 'Yggdrasil'
    foreach ($e in $map.GetEnumerator()) {
        $app, $evt = if ($e.Key -like '*/*') { $e.Key.Split('/') } else { '.Default', $e.Key }
        $wav = Join-Path $Sounds "Yggdrasil - $($e.Value).wav"
        foreach ($slot in 'Yggdrasil', '.Current') {
            $k = "$base\Apps\$app\$evt\$slot"
            Ensure-Key $k
            Set-ItemProperty -Path $k -Name '(default)' -Value $wav
        }
    }
    Set-ItemProperty -Path $base -Name '(default)' -Value 'Yggdrasil'
}

# --------------------------------------------------------------------- 4b. font (per-user)
Say "Installing the Yggdrasil Runic font for your account"
$fontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
New-Item -ItemType Directory -Force -Path $fontDir | Out-Null
$font = Join-Path $fontDir 'YggdrasilRunic.ttf'
if (Test-Path -LiteralPath "$font.new") { try { Move-Item "$font.new" $font -Force } catch { } }
$newFont = Join-Path $Theme 'Fonts\YggdrasilRunic.ttf'
$same = (Test-Path -LiteralPath $font) -and
        ((Get-FileHash -LiteralPath $font).Hash -eq (Get-FileHash -LiteralPath $newFont).Hash)
if (-not $same) {
    try { Copy-Item $newFont $font -Force }
    catch { Say "The font is in use; the new one goes in next time you run Install.ps1 after signing in again" 'Yellow'
            Copy-Item $newFont "$font.new" -Force }   # swapped in on the next run
}
Ensure-Key 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts' -Name 'Yggdrasil Runic (TrueType)' -Value $font

# --------------------------------------------------------------------- 4c. lock screen (WinRT, per-user)
if (-not $NoLockScreen) {
    if ($PSVersionTable.PSEdition -ne 'Desktop') {
        Say "Lock screen skipped: run this in Windows PowerShell (powershell.exe), not pwsh" 'Yellow'
    } else {
        try {
            Add-Type -AssemblyName System.Runtime.WindowsRuntime
            $null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
            $null = [Windows.System.UserProfile.LockScreen, Windows.System.UserProfile, ContentType = WindowsRuntime]
            $ext = [System.WindowsRuntimeSystemExtensions].GetMethods()
            $asOp = ($ext | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
            $asAct = ($ext | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
            $t = $asOp.MakeGenericMethod([Windows.Storage.StorageFile]).Invoke($null, @([Windows.Storage.StorageFile]::GetFileFromPathAsync((Join-Path $Theme 'LockScreen.jpg'))))
            $t.Wait(); $file = $t.Result
            $t2 = $asAct.Invoke($null, @([Windows.System.UserProfile.LockScreen]::SetImageFileAsync($file))); $t2.Wait()
            Say "Lock screen set (turn off Windows Spotlight in Settings > Personalization > Lock screen if it comes back)"
        } catch {
            Say "Couldn't set the lock screen automatically: set $Theme\LockScreen.jpg in Settings > Personalization > Lock screen" 'Yellow'
        }
    }
}

# --------------------------------------------------------------------- 4c2. fastfetch
$ffConfig = Join-Path $Theme 'Fastfetch\yggdrasil.jsonc'
$tmpl = Get-Content -LiteralPath (Join-Path $Theme 'Fastfetch\config.jsonc') -Raw
$logo = (Join-Path $Theme 'Fastfetch\logo.txt').Replace('\', '\\')
[IO.File]::WriteAllText($ffConfig, $tmpl.Replace('__LOGO__', $logo), (New-Object Text.UTF8Encoding $false))
if (-not $NoFastfetch -and -not $NoTerminal -and -not (Get-Command fastfetch -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "Installing fastfetch with winget (your account only, no admin)"
        Start-Process winget -Wait -NoNewWindow -ArgumentList 'install', '--id', 'Fastfetch-cli.Fastfetch', '--exact',
            '--source', 'winget', '--scope', 'user', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity'
    } else {
        Say "winget isn't available, so the Terminal shows the rune banner instead of fastfetch" 'Yellow'
    }
}

# --------------------------------------------------------------------- 4d. Windows Terminal fragment
if (-not $NoTerminal) {
    Say "Adding the Yggdrasil Windows Terminal profile"
    $frag = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows Terminal\Fragments\Yggdrasil'
    New-Item -ItemType Directory -Force -Path $frag | Out-Null
    $banner = @'
function prompt { Write-Host 'ᚨ ' -NoNewline -ForegroundColor DarkYellow; Write-Host $PWD -NoNewline -ForegroundColor Cyan; ' › ' }
if (Get-Command fastfetch -ErrorAction SilentlyContinue) { fastfetch -c '__FF__' } else { Write-Host ''; Write-Host '   ᚨ ᛚ ᛚ ᚠ ᚨ ᚦ ᛖ ᚱ' -ForegroundColor Yellow; Write-Host '' }
'@ -replace "`r?`n", '; '
    $banner = $banner.Replace('__FF__', $ffConfig)
    $json = [ordered]@{
        profiles = @([ordered]@{
            guid                       = '{6b1f3d2a-6f8e-4b0a-9c51-79a0e0c8a25a}'
            name                       = 'Yggdrasil'
            commandline                = 'powershell.exe -NoLogo -NoExit -Command "' + $banner.Replace('"', '\"') + '"'
            icon                       = (Join-Path $Theme 'yggdrasil.ico')
            colorScheme                = 'Yggdrasil'
            cursorColor                = '#C8A25A'
            tabColor                   = '#0B1220'
            backgroundImage            = (Join-Path $Theme 'Wallpapers\Yggdrasil - WorldTree.jpg')
            backgroundImageOpacity     = 0.10
            backgroundImageStretchMode = 'uniformToFill'
            font                       = @{ face = 'Cascadia Mono' }
        })
        schemes = @([ordered]@{
            name = 'Yggdrasil'
            background = '#0B1220'; foreground = '#E8DCC4'; cursorColor = '#C8A25A'; selectionBackground = '#2A2F36'
            black = '#1E2430'; red = '#D65C46'; green = '#80B270'; yellow = '#C8A25A'
            blue = '#6096C4'; purple = '#A082C8'; cyan = '#60B4B4'; white = '#C8BEAA'
            brightBlack = '#505868'; brightRed = '#F07860'; brightGreen = '#A0CE8C'; brightYellow = '#ECD08F'
            brightBlue = '#8FC4E0'; brightPurple = '#BEA5E1'; brightCyan = '#8CD2CD'; brightWhite = '#F5ECD7'
        })
    }
    # UTF-8 without BOM, as Windows Terminal expects
    [IO.File]::WriteAllText((Join-Path $frag 'yggdrasil.json'), ($json | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
}

# --------------------------------------------------------------------- 4e. cursors
$Cursors = Join-Path $Theme 'Cursors'
$roles = 'Arrow','Help','AppStarting','Wait','Crosshair','IBeam','NWPen','No','SizeNS','SizeWE','SizeNWSE','SizeNESW','SizeAll','UpArrow','Hand','Pin','Person'
$cursorPath = @{}
foreach ($r in $roles) {
    $f = Get-ChildItem -LiteralPath $Cursors -Filter "Yggdrasil $r.*" | Select-Object -First 1
    $cursorPath[$r] = $f.FullName
}
if (-not $NoCursors) {
    Say "Registering the Yggdrasil pointer scheme"
    Ensure-Key 'HKCU:\Control Panel\Cursors\Schemes'
    Set-ItemProperty 'HKCU:\Control Panel\Cursors\Schemes' -Name 'Yggdrasil' -Value (($roles | ForEach-Object { $cursorPath[$_] }) -join ',')
}

# --------------------------------------------------------------------- 4f. folder icons
$Icons = Join-Path $Theme 'Icons'
. (Join-Path $Theme 'Set-FolderIcon.ps1')          # Set-YggdrasilFolderIcon, shared with the helper
if (-not $NoFolderIcons) {
    Say "Carving shields onto Documents, Downloads, Pictures, Music and Videos"
    $shell = New-Object -ComObject Shell.Application
    $folders = [ordered]@{
        'Documents' = [Environment]::GetFolderPath('MyDocuments')
        'Downloads' = $shell.NameSpace('shell:Downloads').Self.Path
        'Pictures'  = [Environment]::GetFolderPath('MyPictures')
        'Music'     = [Environment]::GetFolderPath('MyMusic')
        'Videos'    = [Environment]::GetFolderPath('MyVideos')
    }
    foreach ($f in $folders.GetEnumerator()) {
        if ($f.Value -and (Test-Path -LiteralPath $f.Value)) {
            try { Set-YggdrasilFolderIcon -Path $f.Value -Icon $f.Key -Backup $Backup }
            catch { Say "Couldn't set the icon on $($f.Value): $($_.Exception.Message)" 'Yellow' }
        }
    }
}

# --------------------------------------------------------------------- 4g. Rainmeter clock + meters
if (-not $NoWidgets) {
    $rm = @("$env:ProgramFiles\Rainmeter\Rainmeter.exe", "${env:ProgramFiles(x86)}\Rainmeter\Rainmeter.exe") |
          Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if (-not $rm) {
        Say "Rainmeter isn't installed. For the clock and meters run:  winget install Rainmeter.Rainmeter  (it asks for admin), then Install.ps1 again" 'Yellow'
    } else {
        Say "Adding the Yggdrasil clock and meters to Rainmeter"
        $skins = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Rainmeter\Skins'
        $rmIni = Join-Path $env:APPDATA 'Rainmeter\Rainmeter.ini'
        if (Test-Path -LiteralPath $rmIni) {
            $line = Select-String -LiteralPath $rmIni -Pattern '^\s*SkinPath\s*=\s*(.+)$' | Select-Object -First 1
            if ($line) { $skins = $line.Matches[0].Groups[1].Value.Trim() }
        }
        New-Item -ItemType Directory -Force -Path $skins | Out-Null
        Copy-Item -Path (Join-Path $Theme 'Rainmeter\Yggdrasil') -Destination $skins -Recurse -Force
        if (-not (Get-Process Rainmeter -ErrorAction SilentlyContinue)) { Start-Process $rm; Start-Sleep -Seconds 4 }
        Add-Type -AssemblyName System.Windows.Forms
        $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
        $x = $wa.Right - 560 - 48; $y = $wa.Top + 48
        Start-Process $rm -ArgumentList '!RefreshApp' -Wait; Start-Sleep -Seconds 2
        foreach ($w in @(@('Clock', $y), @('Meters', $y + 232 + 16))) {
            $cfg = "Yggdrasil\$($w[0])"
            Start-Process $rm -Wait -ArgumentList "[!ActivateConfig `"$cfg`" `"$($w[0]).ini`"][!Move `"$x`" `"$($w[1])`" `"$cfg`"][!ZPos `"-2`" `"$cfg`"]"
        }
    }
}

# --------------------------------------------------------------------- 5. theme file
Say "Writing and applying Yggdrasil.theme"
$themeFile = Join-Path $Theme 'Yggdrasil.theme'
$soundLine = if ($NoSounds) { '' } else { "[Sounds]`r`nSchemeName=Yggdrasil`r`n" }
$cursorLines = if ($NoCursors) { '' } else {
    "[Control Panel\Cursors]`r`n" + (($roles | ForEach-Object { "$_=$($cursorPath[$_])" }) -join "`r`n") + "`r`nDefaultValue=Yggdrasil`r`n"
}
@"
; Yggdrasil for Windows 11 - generated by Install.ps1
[Theme]
DisplayName=Yggdrasil
ThemeId={8C3A9F1E-2B7D-4E61-A0C8-A25A0B1220E8}

[Control Panel\Desktop]
Wallpaper=$Wall
TileWallpaper=0
WallpaperStyle=10
Pattern=

[VisualStyles]
Path=%SystemRoot%\resources\themes\Aero\Aero.msstyles
ColorStyle=NormalColor
Size=NormalSize
AutoColorization=0
ColorizationColor=0XC4C8A25A
SystemMode=Dark
AppMode=Dark

$soundLine
$cursorLines
[CLSID\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\DefaultIcon]
DefaultValue=$Icons\This PC.ico,0

[CLSID\{59031A47-3F72-44A7-89C5-5595FE6B30EE}\DefaultIcon]
DefaultValue=$Icons\User.ico,0

[CLSID\{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}\DefaultIcon]
DefaultValue=$Icons\Network.ico,0

[CLSID\{645FF040-5081-101B-9F08-00AA002F954E}\DefaultIcon]
Full=$Icons\Recycle Bin Full.ico,0
Empty=$Icons\Recycle Bin Empty.ico,0

[MasterThemeSelector]
MTSM=RJSPBS
"@ | Set-Content -LiteralPath $themeFile -Encoding Unicode

# Dark taskbar and Start with gold highlights; window title bars stay dark.
$p = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
Set-ItemProperty $p -Name AppsUseLightTheme -Value 0 -Type DWord
Set-ItemProperty $p -Name SystemUsesLightTheme -Value 0 -Type DWord
Set-ItemProperty $p -Name ColorPrevalence -Value 0 -Type DWord
Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\DWM' -Name ColorPrevalence -Value 0 -Type DWord

Start-Process -FilePath $themeFile      # Windows applies it and opens Settings > Themes
Start-Sleep -Seconds 2
Start-Process ie4uinit.exe -ArgumentList '-show' -Wait -WindowStyle Hidden   # refresh Explorer's icon cache (per-user)

# --------------------------------------------------------------------- 6. Yggdrasil Sky
if (-not $NoSky) {
    $exe = Join-Path $SkyDir 'YggdrasilSky.exe'
    Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'YggdrasilSky' -Value "`"$exe`" --startup"
    Start-Sleep -Seconds 3
    Start-Process -FilePath $exe
    Say "Yggdrasil Sky is running (tray icon: demo, pause, quit). Windows SmartScreen may ask once: it's unsigned."
}

Write-Host ''
Say "Done. Skål!" 'DarkGreen'
