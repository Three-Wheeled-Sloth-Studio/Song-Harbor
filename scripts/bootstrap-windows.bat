@echo off
setlocal EnableExtensions
rem Song Harbor Windows setup launcher. Work/data root defaults to C:\Apps\SongHarbor.
rem Pass an alternate root as the first argument if needed.
set "SCRIPT_DIR=%~dp0"
set "WORK_ROOT=C:\Apps\SongHarbor"
if not "%~1"=="" set "WORK_ROOT=%~1"

where pwsh.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell 7 is required but pwsh.exe is not on PATH.
  echo Install PowerShell 7, then run this launcher again.
  pause
  exit /b 1
)

echo Song Harbor bootstrap
echo   Work root: "%WORK_ROOT%"
echo   Script: "%SCRIPT_DIR%bootstrap-windows.ps1"
echo.
pwsh.exe -NoProfile -File "%SCRIPT_DIR%bootstrap-windows.ps1" -Root "%WORK_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo Song Harbor setup failed with exit code %EXIT_CODE%.
) else (
  echo Song Harbor environment setup finished.
  echo To start the UI, run scripts\launch-song-harbor.bat
)
pause
exit /b %EXIT_CODE%
