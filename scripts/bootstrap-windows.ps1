#Requires -Version 7.0
<#
.SYNOPSIS
  Bootstrap Song Harbor's Windows CUDA 12.6 separator and M0 UI without altering other Python environments.
.EXAMPLE
  ./scripts/bootstrap-windows.ps1 -Root 'D:\Apps\SongHarbor'
.NOTES
  Python 3.11 x64, NVIDIA CUDA driver >=12.6, FFmpeg, Git and npm are prerequisites.
  If Python 3.11 is not installed, uv can supply it (the script will not install system software).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Root,
  [switch]$SkipModel,
  [switch]$SkipUI
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repoRoot = Split-Path -Parent $PSScriptRoot
$root = [IO.Path]::GetFullPath($Root)
$venvDir = Join-Path $root ".venv"
$python = Join-Path $venvDir "Scripts\python.exe"
$modelDir = Join-Path $root "models"
$env:PIP_CACHE_DIR = Join-Path $root "cache\pip"
$env:HF_HOME = Join-Path $root "cache\huggingface"
$env:TORCH_HOME = Join-Path $root "cache\torch"
$env:TEMP = Join-Path $root "temp"
$env:TMP = $env:TEMP
$env:SONG_HARBOR_HOME = $root
$env:SONG_HARBOR_MODELS = $modelDir

function Run([string]$Program, [string[]]$Arguments) {
  Write-Host (" > " + $Program + " " + ($Arguments -join " "))
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $Program" }
}
function PythonIsCompatible([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  & $Path -c 'import sys; assert sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32'
  return $LASTEXITCODE -eq 0
}
Write-Host "=== Song Harbor Windows bootstrap ==="
Write-Host "Repo:   $repoRoot"
Write-Host "Root:   $root"
Write-Host "Models: $modelDir"
Write-Host "Cache:  $env:PIP_CACHE_DIR"
Write-Host "Venv:   $venvDir"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git is required to fetch TWS UI. Install Git first." }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "FFmpeg not found in PATH. Install it before continuing." }
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { throw "No NVIDIA driver utility found. CUDA GPU bootstrap cannot continue." }
if (-not $SkipUI -and -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
  throw "Node.js/npm is needed for the UI. Install Node.js, or run with -SkipUI."
}
$gpu = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
if ($LASTEXITCODE -ne 0 -or -not $gpu) { throw "NVIDIA GPU inventory failed." }
Write-Host "GPU: $($gpu -join '; ')"
$driverReport = (& nvidia-smi) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "Cannot read NVIDIA driver capabilities." }
$cudaMatch = [regex]::Match($driverReport, '(?:CUDA Version|CUDA UMD Version)\s*:\s*(\d+)\.(\d+)')
if ($cudaMatch.Success) {
  $cudaVersion = [version]("$($cudaMatch.Groups[1].Value).$($cudaMatch.Groups[2].Value)")
  if ($cudaVersion -lt [version]"12.6") { throw "NVIDIA driver CUDA capability $cudaVersion is below required 12.6. Update the driver before installing." }
  Write-Host "Driver CUDA capability: $cudaVersion"
} else {
  Write-Warning "Could not parse driver's maximum CUDA version. PyTorch runtime will be tested explicitly."
}
$driveRoot = [IO.Path]::GetPathRoot($root)
if (-not (Test-Path -LiteralPath $driveRoot)) { throw "Drive not available: $driveRoot" }
$free = (Get-PSDrive -Name $driveRoot.Substring(0,1)).Free
if ($free -lt 12GB) { throw "Selected drive has less than 12 GiB free; choose a larger work drive." }
foreach ($p in @($root,$modelDir,$env:PIP_CACHE_DIR,$env:HF_HOME,$env:TORCH_HOME,$env:TEMP)) {
  New-Item -ItemType Directory -Force -Path $p | Out-Null
}
$base = $null
if (-not (Test-Path -LiteralPath $python)) {
  $candidates = [System.Collections.Generic.List[string]]::new()
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    $found = (& uv python find 3.11 --no-project 2>$null)
    if ($LASTEXITCODE -eq 0 -and $found) { $candidates.Add(($found | Select-Object -First 1).Trim()) }
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($qualifier in @("-3.11-64", "-3.11")) {
      $found = (& py $qualifier -c 'import sys;print(sys.executable)' 2>$null)
      if ($LASTEXITCODE -eq 0 -and $found) { $candidates.Add(($found | Select-Object -First 1).Trim()) }
    }
  }
  foreach ($candidate in $candidates) {
    if (PythonIsCompatible $candidate) { $base = $candidate; break }
  }
  if (-not $base) { throw "Python 3.11 x64 not found. Install using 'uv python install 3.11' (if uv is installed), then rerun." }
  Write-Host "Python 3.11 x64: $base"
  Run $base @("-m","venv",$venvDir)
}
if (-not (PythonIsCompatible $python)) { throw "Existing venv incompatible. Expected 64-bit Python 3.11 at $python; no existing environment was modified." }
Run $python @("-m","pip","install","--upgrade","pip","setuptools","wheel")
$constraints = Join-Path $root "constraints.txt"
@'
torch==2.6.0+cu126
torchvision==0.21.0+cu126
torchaudio==2.6.0+cu126
onnxruntime-gpu==1.24.4
'@ | Set-Content -LiteralPath $constraints -Encoding utf8
Write-Host "Constraints: $constraints"
# Install CUDA build explicitly BEFORE audio-separator to avoid CPU-only dependency substitution.
Run $python @("-m","pip","install",
  "torch==2.6.0+cu126","torchvision==0.21.0+cu126","torchaudio==2.6.0+cu126",
  "--index-url","https://download.pytorch.org/whl/cu126")
Run $python @("-m","pip","install","audio-separator[gpu]==0.47.0","-c",$constraints)
# ONNX Runtime 1.31 selects CUDA 13; force matching tested 1.24.4 to avoid missing CUDA 13 DLLs.
Run $python @("-m","pip","install","--no-deps","onnxruntime-gpu==1.24.4")
Run $python @("-m","pip","install","-r",(Join-Path $repoRoot "app\backend\requirements.txt"),"-c",$constraints)
Run $python @("-m","pip","check")
Run $python @("-c",@'
import torch, torchaudio, onnxruntime as ort
assert torch.__version__ == "2.6.0+cu126", torch.__version__
assert torch.cuda.is_available(), "PyTorch CUDA is not available"
print("GPU:", torch.cuda.get_device_name(0))
x = torch.randn(256, 256, device="cuda")
torch.cuda.synchronize()
assert (x @ x).is_cuda
assert "CUDAExecutionProvider" in ort.get_available_providers(), ort.get_available_providers()
print("PyTorch", torch.__version__, "ONNX", ort.__version__, "CUDA provider visible")
'@)
$separator = Join-Path $venvDir "Scripts\audio-separator.exe"
Run $separator @("--env_info")
if (-not $SkipModel) {
  # Download only; weights' commercial redistribution terms are not yet approved.
  Run $separator @("--download_model_only","--model_filename","htdemucs_6s.yaml","--model_file_dir",$modelDir)
}
if (-not $SkipUI) {
  $frontend = Join-Path $repoRoot "app\frontend"
  Push-Location $frontend
  try {
    Run "npm.cmd" @("install")
    Run "npm.cmd" @("run","build")
  } finally { Pop-Location }
}
Write-Host ""
Write-Host "=== Setup validated (environment only) ==="
Write-Host "Machine: $env:COMPUTERNAME"
Write-Host "Model root: $modelDir"
Write-Host "Run UI: .\app\run.ps1 -Root '$root'"
Write-Host "Still required: process a real song and verify stems. Provider listing alone does not prove inference."
