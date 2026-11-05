#Requires -Version 5.1
<#
.SYNOPSIS
  Removes Yggdrasil for Windows and restores what Install.ps1 backed up.
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Uninstall.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Say($msg, $color = 'DarkYellow') { Write-Host "  * $msg" -ForegroundColor $color }

$Root   = Join-Path $env:LOCALAPPDATA 'Yggdrasil'
$Backup = Join-Path $Root 'Backup'
$SkyDir = Join-Path $env:LOCALAPPDATA 'Programs\YggdrasilSky'

Say "Stopping Yggdrasil Sky"
Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'YggdrasilSky' -ErrorAction SilentlyContinue
Stop-Process -Name YggdrasilSky -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800

Say "Removing the Yggdrasil sound scheme"
$base = 'HKCU:\AppEvents\Schemes'
Get-ChildItem "$base\Apps" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -eq 'Yggdrasil' } | Remove-Item -Recurse -Force
Remove-Item "$base\Names\Yggdrasil" -Recurse -Force -ErrorAction SilentlyContinue

Say "Taking the shields off your folders and desktop icons"
$helper = Join-Path $Root 'Theme\Set-FolderIcon.ps1'
if (Test-Path -LiteralPath $helper) {
    . $helper
    try { Reset-YggdrasilFolderIcon -All -Backup $Backup } catch { Say "Folder icons: $($_.Exception.Message)" 'Yellow' }
}
foreach ($clsid in '{20D04FE0-3AEA-1069-A2D8-08002B30309D}', '{59031A47-3F72-44A7-89C5-5595FE6B30EE}',
                   '{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}', '{645FF040-5081-101B-9F08-00AA002F954E}') {
    Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\CLSID\$clsid\DefaultIcon" -Recurse -Force -ErrorAction SilentlyContinue
}
Remove-ItemProperty 'HKCU:\Control Panel\Cursors\Schemes' -Name 'Yggdrasil' -ErrorAction SilentlyContinue

if (Test-Path (Join-Path $Backup 'done')) {
    Say "Restoring your saved settings"
    foreach ($f in Get-ChildItem $Backup -Filter *.reg) {
        Start-Process reg.exe -ArgumentList 'import', "`"$($f.FullName)`"" -Wait -WindowStyle Hidden
    }
    $cur = Join-Path $Backup 'CurrentTheme.txt'
    if (Test-Path $cur) {
        $t = (Get-Content -LiteralPath $cur -Raw).Trim()
        if ($t -and (Test-Path -LiteralPath ([Environment]::ExpandEnvironmentVariables($t)))) {
            Start-Process -FilePath ([Environment]::ExpandEnvironmentVariables($t))   # re-applies your old wallpaper, colours, sounds
        }
    }
} else {
    Say "No backup found: switch theme in Settings > Personalization > Themes" 'Yellow'
}

# Reload pointers and icons so nothing still points at files about to be deleted.
Add-Type -Namespace Ygg -Name Spi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SystemParametersInfo(uint a, uint b, System.IntPtr c, uint d);'
[void][Ygg.Spi]::SystemParametersInfo(0x57, 0, [IntPtr]::Zero, 3)     # SPI_SETCURSORS
Start-Process ie4uinit.exe -ArgumentList '-show' -Wait -WindowStyle Hidden

Say "Removing the font and the Terminal profile"
Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts' -Name 'Yggdrasil Runic (TrueType)' -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts\YggdrasilRunic.ttf') -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:LOCALAPPDATA 'Microsoft\Windows Terminal\Fragments\Yggdrasil') -Recurse -Force -ErrorAction SilentlyContinue

Say "Removing files"
Remove-Item $SkyDir -Recurse -Force -ErrorAction SilentlyContinue
# The theme folder goes last: the old theme may still be reading from it for a moment.
Start-Sleep -Seconds 3
Remove-Item $Root -Recurse -Force -ErrorAction SilentlyContinue

Say "Done. The lock screen keeps the Fjord until you pick another in Settings > Personalization > Lock screen." 'DarkGreen'
