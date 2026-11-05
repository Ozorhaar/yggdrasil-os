<#
.SYNOPSIS
  Puts a Yggdrasil shield icon on any folder, or takes it off again.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Yggdrasil\Theme\Set-FolderIcon.ps1" -Path D:\Games -Icon Games
.EXAMPLE
  ... Set-FolderIcon.ps1 -Path D:\Games -Reset

  Icons: Folder, Documents, Downloads, Pictures, Music, Videos, Games, Code, Projects, Archive
  (plus This PC, User, Network). Uses the folder's own desktop.ini, the standard Windows
  mechanism; the original is saved first and Uninstall.ps1 puts every folder back.
#>
[CmdletBinding()]
param([string]$Path, [string]$Icon = 'Folder', [switch]$Reset)

$script:YggIcons = Join-Path $PSScriptRoot 'Icons'
$script:YggBackup = Join-Path $env:LOCALAPPDATA 'Yggdrasil\Backup'

function Get-YggFolderMap([string]$Backup) {
    $file = Join-Path $Backup 'FolderIcons.json'
    $map = @{}
    if (Test-Path -LiteralPath $file) {
        (Get-Content -LiteralPath $file -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $map[$_.Name] = $_.Value }
    }
    return $map
}

function Save-YggFolderMap([hashtable]$map, [string]$Backup) {
    New-Item -ItemType Directory -Force -Path $Backup | Out-Null
    $map | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $Backup 'FolderIcons.json') -Encoding UTF8
}

function Set-YggdrasilFolderIcon {
    param([Parameter(Mandatory)][string]$Path, [string]$Icon = 'Folder', [string]$Backup = $script:YggBackup)
    $Path = (Resolve-Path -LiteralPath $Path).Path
    $ico = Join-Path $script:YggIcons "$Icon.ico"
    if (-not (Test-Path -LiteralPath $ico)) { throw "No icon called '$Icon' in $script:YggIcons" }
    $ini = Join-Path $Path 'desktop.ini'
    $dir = Get-Item -LiteralPath $Path -Force

    # Save the original once (content + folder attributes) so it can be put back exactly.
    $map = Get-YggFolderMap $Backup
    if (-not $map.ContainsKey($Path)) {
        $orig = if (Test-Path -LiteralPath $ini) { [Convert]::ToBase64String([IO.File]::ReadAllBytes($ini)) } else { $null }
        $map[$Path] = [pscustomobject]@{ ini = $orig; attributes = [int]$dir.Attributes }
        Save-YggFolderMap $map $Backup
    }

    # Rewrite [.ShellClassInfo] with our IconResource, keeping everything else.
    $lines = if (Test-Path -LiteralPath $ini) { @(Get-Content -LiteralPath $ini) } else { @() }
    $out = New-Object System.Collections.Generic.List[string]
    $inShell = $false; $done = $false
    foreach ($l in $lines) {
        if ($l -match '^\s*\[(.+)\]\s*$') {
            if ($inShell -and -not $done) { $out.Add("IconResource=$ico,0"); $done = $true }
            $inShell = $Matches[1] -eq '.ShellClassInfo'
            $out.Add($l); continue
        }
        if ($inShell -and $l -match '^\s*(IconResource|IconFile|IconIndex)\s*=') { continue }
        $out.Add($l)
    }
    if ($inShell -and -not $done) { $out.Add("IconResource=$ico,0"); $done = $true }
    if (-not $done) { $out.Insert(0, "IconResource=$ico,0"); $out.Insert(0, '[.ShellClassInfo]') }

    if (Test-Path -LiteralPath $ini) { (Get-Item -LiteralPath $ini -Force).Attributes = 'Normal' }
    Set-Content -LiteralPath $ini -Value $out -Encoding Unicode
    (Get-Item -LiteralPath $ini -Force).Attributes = 'Hidden, System'
    $dir.Attributes = $dir.Attributes -bor [IO.FileAttributes]::ReadOnly   # Explorer only reads desktop.ini on read-only/system folders
}

function Reset-YggdrasilFolderIcon {
    param([string]$Path, [switch]$All, [string]$Backup = $script:YggBackup)
    $map = Get-YggFolderMap $Backup
    $targets = if ($All) { @($map.Keys) } else { @((Resolve-Path -LiteralPath $Path).Path) }
    foreach ($p in $targets) {
        if (-not $map.ContainsKey($p) -or -not (Test-Path -LiteralPath $p)) { continue }
        $ini = Join-Path $p 'desktop.ini'
        if (Test-Path -LiteralPath $ini) { (Get-Item -LiteralPath $ini -Force).Attributes = 'Normal' }
        $o = $map[$p]
        if ($o.ini) {
            [IO.File]::WriteAllBytes($ini, [Convert]::FromBase64String($o.ini))
            (Get-Item -LiteralPath $ini -Force).Attributes = 'Hidden, System'
        } elseif (Test-Path -LiteralPath $ini) {
            Remove-Item -LiteralPath $ini -Force
        }
        (Get-Item -LiteralPath $p -Force).Attributes = [IO.FileAttributes]$o.attributes
        $map.Remove($p)
    }
    Save-YggFolderMap $map $Backup
}

# Run directly (not dot-sourced by Install.ps1 / Uninstall.ps1)
if ($MyInvocation.InvocationName -ne '.' -and $Path) {
    if ($Reset) { Reset-YggdrasilFolderIcon -Path $Path } else { Set-YggdrasilFolderIcon -Path $Path -Icon $Icon }
    Start-Process ie4uinit.exe -ArgumentList '-show' -Wait -WindowStyle Hidden
    Write-Host "Done: $Path"
}
