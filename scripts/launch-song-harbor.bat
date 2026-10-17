@echo off
setlocal EnableExtensions
rem Launch Song Harbor M0 UI using the installed local Python environment.
set "SCRIPT_DIR=%~dp0"
set "WORK_ROOT=C:\Apps\SongHarbor"
if not "%~1"=="" set "WORK_ROOT=%~1"

where pwsh.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell 7 is required but pwsh.exe is not on PATH.
  pause
  exit /b 1
)
pwsh.exe -NoProfile -File "%SCRIPT_DIR%..\app\run.ps1" -Root "%WORK_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo Song Harbor exited with code %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%
