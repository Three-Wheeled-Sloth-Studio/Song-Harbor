#Requires -Version 7.0
<#
  Launch an isolated Song Harbor dev checkout without changing the main checkout.
  The dev checkout's existing update script fast-forwards origin/dev; the
  in-app update/relaunch path also follows the checked-out branch.
#>
[CmdletBinding()]
param([string]$Root = "")
$ErrorActionPreference = 'Stop'
$mainRepository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$parent = Split-Path -Parent $mainRepository
$devRepository = [IO.Path]::GetFullPath((Join-Path $parent ((Split-Path -Leaf $mainRepository) + '-Dev')))
$runtimeRoot = if ($Root) {
  [IO.Path]::GetFullPath($Root)
} else {
  [IO.Path]::GetFullPath((Join-Path $parent 'SongHarborDev'))
}
$productionRuntime = [IO.Path]::GetFullPath((Join-Path $parent 'SongHarbor'))
$gitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $gitCommand) { $gitCommand = Get-Command git -ErrorAction Stop }
$git = $gitCommand.Source
if (-not (Test-Path -LiteralPath (Join-Path $mainRepository '.git'))) {
  throw 'Dev launcher must be started from the main Song Harbor Git checkout.'
}
$currentBranch = (& $git -C $mainRepository branch --show-current)
if ($LASTEXITCODE -ne 0 -or $currentBranch.Trim() -ne 'main') {
  throw 'Run this launcher from the main checkout. It will not switch branches.'
}
if ($runtimeRoot.Equals($productionRuntime,[StringComparison]::OrdinalIgnoreCase) -or
    $runtimeRoot.Equals($mainRepository,[StringComparison]::OrdinalIgnoreCase) -or
    $runtimeRoot.Equals($devRepository,[StringComparison]::OrdinalIgnoreCase) -or
    ($env:SONG_HARBOR_HOME -and
      $runtimeRoot.Equals([IO.Path]::GetFullPath($env:SONG_HARBOR_HOME),[StringComparison]::OrdinalIgnoreCase))) {
  throw 'Dev runtime must be separate from production and source directories.'
}
$origin = (& $git -C $mainRepository remote get-url origin)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($origin)) {
  throw 'Main checkout has no origin remote. Cannot create dev checkout.'
}
if (-not (Test-Path -LiteralPath $devRepository)) {
  Write-Host "Creating isolated dev checkout at $devRepository"
  & $git clone --branch dev --single-branch -- $origin.Trim() $devRepository
  if ($LASTEXITCODE -ne 0) {
    throw 'Could not clone origin/dev. No main checkout files were changed.'
  }
}
if (-not (Test-Path -LiteralPath (Join-Path $devRepository '.git'))) {
  throw "Refusing to use an existing non-Git directory: $devRepository"
}
$devBranch = (& $git -C $devRepository branch --show-current)
if ($LASTEXITCODE -ne 0 -or $devBranch.Trim() -ne 'dev') {
  throw "Dev checkout must be on dev; found '$devBranch'. No branch changes were made."
}
$devOrigin = (& $git -C $devRepository remote get-url origin)
if ($LASTEXITCODE -ne 0 -or $devOrigin.Trim() -ne $origin.Trim()) {
  throw 'Existing dev checkout uses a different origin. Refusing to update it.'
}
$start = Join-Path $devRepository 'scripts\start-song-harbor.ps1'
if (-not (Test-Path -LiteralPath $start -PathType Leaf)) {
  throw 'Dev checkout does not contain the standard Song Harbor launcher.'
}
Write-Host '=== Song Harbor DEV ==='
Write-Host "Source: $devRepository (branch dev)"
Write-Host "Runtime: $runtimeRoot (isolated from production)"
Write-Host 'Updates, including in-app refresh, follow origin/dev from this checkout.'
& $start -Root $runtimeRoot
if (-not $?) { throw 'Dev Song Harbor launcher failed.' }
