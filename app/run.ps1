param([string]$Root = "", [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
if (-not $Root) { $Root = Split-Path -Parent $PSScriptRoot }
$Root = [IO.Path]::GetFullPath($Root)
$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Python environment not found: $python" }
$env:SONG_HARBOR_HOME = $Root
$env:SONG_HARBOR_DATA = Join-Path $Root "data"
$env:SONG_HARBOR_MODELS = Join-Path $Root "models"
$env:PIP_CACHE_DIR = Join-Path $Root "cache\pip"
$env:HF_HOME = Join-Path $Root "cache\huggingface"
$env:TORCH_HOME = Join-Path $Root "cache\torch"
$env:TEMP = Join-Path $Root "temp"
$env:TMP = $env:TEMP
@($env:SONG_HARBOR_DATA,$env:SONG_HARBOR_MODELS,$env:PIP_CACHE_DIR,$env:HF_HOME,$env:TORCH_HOME,$env:TEMP) | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
Write-Host "Data: $env:SONG_HARBOR_DATA"
Write-Host "Models: $env:SONG_HARBOR_MODELS"
Write-Host "Caches: $env:PIP_CACHE_DIR"
Write-Host "UI: http://127.0.0.1:5173"
$frontend = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { throw "Frontend dependencies missing. Run npm install in $frontend" }
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$backend = Start-Process -FilePath $python -ArgumentList @((Join-Path $PSScriptRoot "backend\server.py")) -WorkingDirectory $Root -PassThru -NoNewWindow
try {
  for ($i=0; $i -lt 30; $i++) {
    try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 1; break } catch { Start-Sleep -Milliseconds 300 }
  }
  if (-not $NoBrowser) {
    $url = "http://127.0.0.1:5173"
    # Ask a supported browser for a separate window instead of an existing tab.
    # Prefer a discoverable Edge/Chrome installation; otherwise honor the system URL handler.
    $browser = $null
    foreach ($name in @("msedge.exe", "chrome.exe")) {
      $found = Get-Command $name -ErrorAction SilentlyContinue
      if ($found) { $browser = $found.Source; break }
    }
    if (-not $browser) {
      foreach ($candidate in @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe")
      )) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
          $browser = $candidate; break
        }
      }
    }
    if ($browser) {
      Start-Process -FilePath $browser -ArgumentList @("--new-window", $url)
    } else {
      Write-Warning "Could not locate Edge/Chrome for forced new window; using system default browser."
      Start-Process $url
    }
  }
  & $npm run dev --prefix $frontend
}
finally {
  if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}
