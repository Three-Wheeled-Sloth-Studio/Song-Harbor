#Requires -Version 7.0
<#
  Portable Windows launcher; shares the same work-root selection with bootstrap.
  Priority: explicit -Root > SONG_HARBOR_HOME > existing sibling/runtime venv
  > repository path when used as a runtime folder > sibling SongHarbor > repo parent.
#>
[CmdletBinding()]
param(
  [string]$Root = "",
  [switch]$NoBrowser,
  [switch]$SkipInstall,
  [switch]$InstallOnly,
  [switch]$ShowRoot
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$repoParent = Split-Path -Parent $repoRoot
function Resolve-WorkRoot {
  param([string]$ExplicitRoot)
  if ($ExplicitRoot) { return [IO.Path]::GetFullPath($ExplicitRoot) }
  if ($env:SONG_HARBOR_HOME) { return [IO.Path]::GetFullPath($env:SONG_HARBOR_HOME) }
  $choices = @(
    $repoRoot,
    $repoParent,
    (Join-Path $repoParent 'SongHarbor'),
    (Join-Path $repoParent 'Song-Harbor'),
    (Join-Path $repoParent 'song-harbor')
  )
  foreach ($candidate in ($choices | Select-Object -Unique)) {
    if (Test-Path -LiteralPath (Join-Path $candidate '.venv\Scripts\python.exe') -PathType Leaf) {
      return [IO.Path]::GetFullPath($candidate)
    }
  }
  # New machine: default to a sibling work root instead of adding model weights to a source checkout.
  return [IO.Path]::GetFullPath((Join-Path $repoParent 'SongHarbor'))
}
$workRoot = Resolve-WorkRoot $Root
$python = Join-Path $workRoot '.venv\Scripts\python.exe'
$separator = Join-Path $workRoot '.venv\Scripts\audio-separator.exe'
$frontend = Join-Path $repoRoot 'app\frontend'
$nodeModules = Join-Path $frontend 'node_modules'
Write-Host '=== Song Harbor portable launch ==='
Write-Host "Source: $repoRoot"
Write-Host "Runtime root: $workRoot"
if ($ShowRoot) { return }

$needsPython = -not (Test-Path -LiteralPath $python -PathType Leaf)
$needsSeparator = -not (Test-Path -LiteralPath $separator -PathType Leaf)
$needsBackend = $true
if (-not $needsPython) {
  & $python -c 'import fastapi, uvicorn, multipart, torch; assert torch.cuda.is_available()'
  $needsBackend = $LASTEXITCODE -ne 0
}
$needsUI = -not (Test-Path -LiteralPath $nodeModules -PathType Container)
$needsInstall = $needsPython -or $needsSeparator -or $needsBackend -or $needsUI
if ($needsInstall) {
  if ($SkipInstall) {
    throw "Missing Song Harbor dependencies at $workRoot; rerun without -SkipInstall to install."
  }
  Write-Host 'Missing runtime or UI dependencies; performing one-time bootstrap.'
  & (Join-Path $PSScriptRoot 'bootstrap-windows.ps1') -Root $workRoot
  if (-not $?) { throw 'Bootstrap did not complete successfully.' }
}
if ($InstallOnly) {
  Write-Host 'Song Harbor dependencies are available.'
  return
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw "Python environment unavailable after setup: $python"
}
if (-not (Test-Path -LiteralPath $nodeModules -PathType Container)) {
  throw "UI dependencies unavailable after setup: $nodeModules"
}
& (Join-Path $repoRoot 'app\run.ps1') -Root $workRoot -NoBrowser:$NoBrowser
if (-not $?) { throw 'Song Harbor runtime exited with an error.' }
