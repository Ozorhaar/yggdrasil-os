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
