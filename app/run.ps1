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
    $launched = $false
    # Respect the Windows HTTP UserChoice association. Never pick another browser
    # merely because its executable is installed or happens to be on PATH.
    try {
      $choiceKey = 'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice'
      $progId = (Get-ItemProperty -LiteralPath $choiceKey -ErrorAction Stop).ProgId
      if ($progId) {
        $commandKey = "Registry::HKEY_CLASSES_ROOT\$progId\shell\open\command"
        $commandText = (Get-Item -LiteralPath $commandKey -ErrorAction Stop).GetValue('')
        $exePath = $null
        if ($commandText -match '^\s*"([^"]+\.exe)"') {
          $exePath = $Matches[1]
        } elseif ($commandText -match '^\s*(.+?\.exe)(?=\s|$)') {
          $exePath = $Matches[1]
        }
        if ($exePath -and (Test-Path -LiteralPath $exePath -PathType Leaf)) {
          $binaryName = [IO.Path]::GetFileName($exePath).ToLowerInvariant()
          $windowSwitch = switch ($binaryName) {
            'chrome.exe'  { '--new-window' }
            'msedge.exe'  { '--new-window' }
            'firefox.exe' { '-new-window' }
            'brave.exe'   { '--new-window' }
            'vivaldi.exe' { '--new-window' }
            default       { $null }
          }
          if ($windowSwitch) {
            Start-Process -FilePath $exePath -ArgumentList @($windowSwitch, $url)
            $launched = $true
            Write-Host "Opened in Windows default browser ($binaryName), new window."
          }
        }
      }
    } catch {
      Write-Verbose "Could not resolve browser launch command: $_"
    }
    if (-not $launched) {
      # When Windows' chosen handler cannot be safely launched with a known
      # new-window switch, preserve the default-browser choice over window mode.
      Start-Process $url
      Write-Host "Opened via Windows default HTTP handler."
    }
  }
  & $npm run dev --prefix $frontend
}
finally {
  if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}
