#Requires -Version 7.0
<# User-approved update launcher, independent of the backend being restarted.
   Never reset/stash/force local files; delegates to existing safe updater.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$Repository,
  [Parameter(Mandatory)][string]$RuntimeRoot,
  [Parameter(Mandatory)][int]$PreviousPid
)
$ErrorActionPreference='Stop'
$Repository=[IO.Path]::GetFullPath($Repository)
$RuntimeRoot=[IO.Path]::GetFullPath($RuntimeRoot)
$launcher=Join-Path $Repository 'scripts\start-song-harbor.ps1'
$updater=Join-Path $Repository 'scripts\update-checkout.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf) -or
    -not (Test-Path -LiteralPath $updater -PathType Leaf)) {
  throw 'Song Harbor update scripts are missing. Existing files have not been changed.'
}
Write-Host 'Waiting for old Song Harbor backend to exit...'
for ($i=0;$i -lt 150;$i++) {
  $running=Get-Process -Id $PreviousPid -ErrorAction SilentlyContinue
  if (-not $running) { break }
  Start-Sleep -Milliseconds 200
}
if (Get-Process -Id $PreviousPid -ErrorAction SilentlyContinue) {
  throw 'Old server did not exit; update cancelled. No source files were changed.'
}
Write-Host 'Updating safely (never resetting local changes)...'
& $updater -Repository $Repository
Write-Host 'Rebuilding and relaunching Song Harbor...'
& $launcher -Root $RuntimeRoot -NoUpdate
if (-not $?) { throw 'Relaunch failed. Run the standard Song Harbor batch launcher for diagnostics.' }
