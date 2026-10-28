@echo off
setlocal EnableExtensions
rem Launches an isolated origin/dev checkout; normal launch-song-harbor.bat remains on main.
set "SCRIPT_DIR=%~dp0"
where pwsh.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell 7 is required.
  pause
  exit /b 1
)
if "%~1"=="" (
  pwsh.exe -NoProfile -File "%SCRIPT_DIR%launch-song-harbor-dev.ps1"
) else (
  pwsh.exe -NoProfile -File "%SCRIPT_DIR%launch-song-harbor-dev.ps1" -Root "%~1"
)
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Song Harbor DEV failed with exit code %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%
