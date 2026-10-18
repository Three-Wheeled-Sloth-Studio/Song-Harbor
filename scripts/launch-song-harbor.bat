@echo off
setlocal EnableExtensions
rem Portable launcher. Finds the existing environment beside the checkout,
rem or installs missing libraries in a separate work root.
set "SCRIPT_DIR=%~dp0"
where pwsh.exe >nul 2>&1
if errorlevel 1 (
  echo ERROR: PowerShell 7 is required. Install PowerShell 7 and retry.
  pause
  exit /b 1
)
if "%~1"=="" (
  pwsh.exe -NoProfile -File "%SCRIPT_DIR%start-song-harbor.ps1"
) else (
  pwsh.exe -NoProfile -File "%SCRIPT_DIR%start-song-harbor.ps1" -Root "%~1"
)
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Song Harbor failed with exit code %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%
