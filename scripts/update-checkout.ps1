#Requires -Version 7.0
<#
  Non-destructive update for developer source checkouts.
  Git fast-forward respects unrelated local edits; Git itself refuses conflicts.
  Never reset, clean, force, or stash users' files.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Repository, [switch]$Quiet)
$ErrorActionPreference = 'Stop'
$Repository = [IO.Path]::GetFullPath($Repository)

function Write-Update([string]$message) {
  if (-not $Quiet) { Write-Host $message }
}

$git = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $git) { $git = Get-Command git -ErrorAction SilentlyContinue }
if (-not $git -or -not (Test-Path -LiteralPath (Join-Path $Repository '.git'))) {
  Write-Update "No Git checkout detected; launching installed source."
  return
}

$branch = (& $git.Source -C $Repository branch --show-current 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($branch)) {
  Write-Warning 'Update skipped: checkout is detached or Git branch lookup failed.'
  return
}
$branch = $branch.Trim()
$before = (& $git.Source -C $Repository rev-parse HEAD 2>$null)
if ($LASTEXITCODE -ne 0) { Write-Warning 'Git checkout cannot be read; skipping updates.'; return }

# A dirty checkout alone is NOT a reason to skip updates. Git merge --ff-only
# preserves unrelated modifications and rejects actual overlapping changes.
$dirty = @(& $git.Source -C $Repository status --porcelain 2>$null)
if ($dirty.Count -gt 0) {
  Write-Update "Local checkout changes detected; attempting a safe fast-forward (without touching those files)."
}
Write-Update "Checking origin/$branch for updates..."
& $git.Source -C $Repository fetch --quiet origin $branch
if ($LASTEXITCODE -ne 0) {
  Write-Warning 'Update unavailable (offline/credentials/remote). Launching installed source.'
  return
}

$remote = (& $git.Source -C $Repository rev-parse FETCH_HEAD 2>$null)
if ($LASTEXITCODE -ne 0) { Write-Warning 'Cannot resolve fetched revision; launching installed source.'; return }
if ($before.Trim() -eq $remote.Trim()) {
  Write-Update 'Song Harbor checkout is up to date.'
  return
}
$ancestor = (& $git.Source -C $Repository merge-base HEAD FETCH_HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or $ancestor.Trim() -ne $before.Trim()) {
  Write-Warning 'Update skipped: local and remote history diverged. No files were changed.'
  return
}

# Capture stderr in text instead of allowing PowerShell native stderr preference
# to abort an otherwise recoverable update.
$results = @(& $git.Source -C $Repository -c core.autocrlf=false merge --ff-only FETCH_HEAD 2>&1)
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Update couldn't apply without changing local files. Existing checkout preserved."
  $results | Select-Object -Last 8 | ForEach-Object { Write-Update "  $_" }
  Write-Update "Inspect with: git -C `"$Repository`" status --short"
  return
}
Write-Update "Song Harbor source updated successfully: $($remote.Trim().Substring(0,12))"
