#Requires -Version 7.0
<#
  Free Song Harbor-owned development listeners before launching a replacement.
  Never terminate unrelated listeners or a backend with active render/separation.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Repository)
$ErrorActionPreference = 'Stop'
$Repository = [IO.Path]::GetFullPath($Repository)
$backendScript = [IO.Path]::GetFullPath((Join-Path $Repository 'app\backend\server.py'))
$frontendRoot = [IO.Path]::GetFullPath((Join-Path $Repository 'app\frontend'))
function Get-Owner([int]$Port) {
  $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
  $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
  foreach ($processId in $owners) {
    if (-not $processId) { continue }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    $command = [string]$process.CommandLine
    $baseName = [IO.Path]::GetFileName([string]$process.ExecutablePath)
    $pythonOwned = $Port -eq 8765 -and $baseName -match '^pythonw?(?:3(?:\.\d+)?)?\.exe$' -and
      $command.IndexOf($backendScript, [StringComparison]::OrdinalIgnoreCase) -ge 0
    $viteOwned = $Port -eq 5173 -and $baseName -match '^node\.exe$' -and
      $command.IndexOf($frontendRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and
      $command -match 'vite'
    [pscustomobject]@{Port=$Port;Pid=[int]$processId;Name=$baseName;Owned=($pythonOwned -or $viteOwned)}
  }
}
foreach ($port in @(8765,5173)) {
  foreach ($listener in @(Get-Owner $port)) {
    if (-not $listener.Owned) {
      throw "Port $port is in use by PID $($listener.Pid) ($($listener.Name)), which is not a verified Song Harbor instance. Close that application or free the port, then relaunch. No process was terminated."
    }
    if ($port -eq 8765) {
      try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/runtime/status" -TimeoutSec 2
        if ($status.busy) {
          throw "Song Harbor is processing $($status.active_jobs) job(s) on PID $($listener.Pid). Wait for completion before relaunching; the job has not been interrupted."
        }
      } catch {
        if ($_.Exception.Message -like 'Song Harbor is processing*') { throw }
        # An older Song Harbor may lack /api/runtime/status. Avoid killing a
        # potentially expensive running separation without explicit consent.
        Write-Host "Older Song Harbor backend on PID $($listener.Pid) cannot report active jobs."
        $answer = Read-Host "Restart that verified Song Harbor process? Unsaved in-progress work may stop (y/N)"
        if ($answer -notin @('y','Y','yes','YES')) {
          throw "Existing Song Harbor instance retained; launch cancelled. Close older instance after its jobs finish, then retry."
        }
      }
    }
    Write-Host "Stopping earlier Song Harbor $($listener.Name) on port $port (PID $($listener.Pid))."
    Stop-Process -Id $listener.Pid -Force -ErrorAction Stop
    for ($i=0;$i -lt 30;$i++) {
      Start-Sleep -Milliseconds 150
      if (-not @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue).Count) { break }
    }
    $remaining = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    if ($remaining.Count -gt 0) {
      throw "Port $port is still occupied after restarting the earlier Song Harbor process; retry after closing the previous launcher."
    }
  }
}
