# Song Harbor acoustic artifact verification (Windows PowerShell 7+)
# Read-only against song media and project databases.
param([switch]$SkipInstall,[switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontend = Join-Path $repo 'app/frontend'
$reportDir = Join-Path $env:TEMP 'song-harbor-artifact-qa'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
Push-Location $repo
try {
  if (-not $SkipInstall) {
    & npm.cmd ci --prefix app/frontend
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed with code $LASTEXITCODE" }
  }
  if (-not $SkipBuild) {
    & npm.cmd run build --prefix app/frontend
    if ($LASTEXITCODE -ne 0) { throw "TypeScript/Vite build failed with code $LASTEXITCODE" }
  }
  $tests = @(
    'app/frontend/tests/attack-rise.test.mjs',
    'app/frontend/tests/audio-cleanup.test.mjs',
    'app/frontend/tests/artifact-evaluation.test.mjs',
    'app/frontend/tests/planned-artifact-fixtures.test.mjs'
  )
  & node --experimental-strip-types --test @tests
  if ($LASTEXITCODE -ne 0) { throw "Artifact tests failed with code $LASTEXITCODE" }
  $report = Join-Path $reportDir 'artifact-benchmark.json'
  & node --experimental-strip-types app/frontend/tests/run-artifact-benchmark.mjs | Set-Content -Encoding utf8 $report
  if ($LASTEXITCODE -ne 0) { throw "Artifact benchmark failed with code $LASTEXITCODE" }
  $json = Get-Content -Raw $report | ConvertFrom-Json
  if ($json.kind -ne 'audible-artifact-evaluation' -or $json.totals.cases -lt 9) {
    throw 'Artifact benchmark report missing expected data'
  }
  Write-Host "Artifact suite complete. Inspect $report"
  Write-Host 'Synthetic benchmark metrics are research-only and do not establish audible defect detection.'
} finally {
  Pop-Location
}
