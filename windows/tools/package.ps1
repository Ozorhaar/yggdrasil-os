# Builds Yggdrasil Sky and assembles Yggdrasil-Windows.zip + SHA256SUMS.
# Used by .github/workflows/windows.yml; also works locally on Windows with the .NET 10 SDK:
#   pwsh windows/tools/package.ps1 -Version 1.0.0
param([string]$Version = '0.0.0-dev')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo  = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$out   = Join-Path $repo 'out'
$stage = Join-Path $out 'Yggdrasil-Windows'
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stage | Out-Null

dotnet publish (Join-Path $repo 'windows\sky\YggdrasilSky.csproj') -c Release -o (Join-Path $stage 'sky') -p:Version=$Version
if ($LASTEXITCODE) { throw "dotnet publish failed" }

Copy-Item (Join-Path $repo 'windows\theme') (Join-Path $stage 'theme') -Recurse
Copy-Item (Join-Path $repo 'windows\package\*') $stage

# SHA256SUMS: "<hash>  <relative/path>" for every file, checked by Install.ps1
$lines = Get-ChildItem $stage -Recurse -File | Sort-Object FullName | ForEach-Object {
    $rel = $_.FullName.Substring($stage.Length + 1).Replace('\', '/')
    '{0}  {1}' -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $rel
}
[IO.File]::WriteAllLines((Join-Path $stage 'SHA256SUMS'), $lines)

$zip = Join-Path $out "Yggdrasil-Windows-$Version.zip"
Compress-Archive -Path $stage -DestinationPath $zip
$h = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$h  $(Split-Path $zip -Leaf)" | Set-Content "$zip.sha256" -Encoding ascii
Write-Host "$zip`n$h"
