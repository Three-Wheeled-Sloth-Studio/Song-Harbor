@echo off
setlocal EnableExtensions
rem Portable explicit installer; uses launcher's work-root resolution.
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
echo.
if not "%EXIT_CODE%"=="0" (
  echo Song Harbor setup or launch failed with exit code %EXIT_CODE%.
) else (
  echo Song Harbor exited normally.
)
pause
exit /b %EXIT_CODE%
