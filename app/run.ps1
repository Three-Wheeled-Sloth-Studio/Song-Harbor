#Requires -Version 7.0
<#
  Song Harbor standalone source launcher.
  One Python/FastAPI process serves BOTH the built UI and API.
  No Vite development server, HTTP proxy, fixed port, process killing or
  changes to existing listeners. The OS assigns an available loopback port.
#>
[CmdletBinding()]
param([string]$Root = "", [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = Split-Path -Parent $PSScriptRoot }
$Root = [IO.Path]::GetFullPath($Root)
$python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python environment not found: $python" }

$env:SONG_HARBOR_HOME = $Root
# Working media location is machine-local; models, caches and dependencies remain
# on the runtime drive. Existing projects are never moved automatically.
$dataFolder = Join-Path $Root 'data'
$configPath = Join-Path $Root 'config\settings.json'
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
  try {
    $prefs = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($prefs.working_files_directory) {
      $candidate = [IO.Path]::GetFullPath([string]$prefs.working_files_directory)
      if (-not [IO.Path]::IsPathFullyQualified($candidate)) {
        throw 'Working files directory must be absolute.'
      }
      $dataFolder = $candidate
    }
  } catch {
    throw "Invalid Song Harbor storage settings at $configPath : $_. Edit settings.json or correct the location before launching."
  }
}
$env:SONG_HARBOR_DATA = $dataFolder
$env:SONG_HARBOR_MODELS = Join-Path $Root 'models'
$env:PIP_CACHE_DIR = Join-Path $Root 'cache\pip'
$env:HF_HOME = Join-Path $Root 'cache\huggingface'
$env:TORCH_HOME = Join-Path $Root 'cache\torch'
$env:TEMP = Join-Path $Root 'temp'
$env:TMP = $env:TEMP
@($env:SONG_HARBOR_DATA,$env:SONG_HARBOR_MODELS,$env:PIP_CACHE_DIR,
  $env:HF_HOME,$env:TORCH_HOME,$env:TEMP) | ForEach-Object {
  New-Item -ItemType Directory -Force $_ | Out-Null
}

# Build the frontend *before* serving it. This also catches TSX errors
# before a broken browser page appears. npm/Vite is never left running.
$frontend = Join-Path $PSScriptRoot 'frontend'
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
Push-Location $frontend
try {
  if (-not (Test-Path -LiteralPath 'node_modules' -PathType Container)) {
    Write-Host 'Installing frontend dependencies...'
    & $npm install
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency install failed (exit $LASTEXITCODE)" }
  }
  Write-Host 'Building Song Harbor interface...'
  & $npm run build
  if ($LASTEXITCODE -ne 0) { throw "Frontend build failed (exit $LASTEXITCODE)" }
} finally {
  Pop-Location
}
$index = Join-Path $frontend 'dist\index.html'
if (-not (Test-Path -LiteralPath $index -PathType Leaf)) {
  throw "Frontend build did not produce $index"
}

# Each launch gets a free ephemeral localhost port; existing Song Harbor
# sessions (and completely unrelated programs) are never terminated.
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
try {
  $listener.Start()
  $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port
} finally {
  $listener.Stop()
}
$env:SONG_HARBOR_PORT = [string]$port
$instanceToken = [guid]::NewGuid().ToString('N')
$env:SONG_HARBOR_INSTANCE_TOKEN = $instanceToken
$url = "http://127.0.0.1:$port/"
Write-Host "Data: $env:SONG_HARBOR_DATA"
Write-Host "Models: $env:SONG_HARBOR_MODELS"
Write-Host "UI/API (single server): $url"

$backend = Start-Process -FilePath $python -ArgumentList @(
  ('"' + (Join-Path $PSScriptRoot 'backend\server.py') + '"')
) -WorkingDirectory $Root -PassThru -NoNewWindow
try {
  $ready = $false
  for ($i=0; $i -lt 100; $i++) {
    $backend.Refresh()
    if ($backend.HasExited) {
      throw "Song Harbor process exited during startup (code $($backend.ExitCode)). See console output."
    }
    try {
      $status = Invoke-RestMethod -Uri ($url + 'api/health') -TimeoutSec 2
      $page = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing
      if ($status.instance_token -eq $instanceToken -and
          $null -ne $status.separator_ready -and
          $page.StatusCode -eq 200 -and $page.Content -match '<div id="root"') {
        $ready = $true
        break
      }
    } catch {
      # Startup may take a few seconds on lower-end hardware.
    }
    Start-Sleep -Milliseconds 250
  }
  if (-not $ready) { throw "Song Harbor did not become ready at $url. See console output." }
  if (-not $NoBrowser) {
    $url = "http://127.0.0.1:$port/"
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
  Write-Host 'Song Harbor is ready. Press Ctrl+C here to exit.'
  Wait-Process -Id $backend.Id
} finally {
  $backend.Refresh()
  if (-not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  }
}
