@echo off
setlocal
rem Copy official platform-tools fastboot.exe into PATH or this folder.
rem Usage: flash-rothko.cmd -Image "boot.img" -Manifest "candidate-manifest.json"
rem Optional -Flash is BLOCKED on unapproved manifests.
where powershell.exe >nul 2>&1
if errorlevel 1 (
  echo Windows PowerShell is required.
  exit /b 1
)
powershell.exe -NoProfile -File "%~dp0Flash-Rothko.ps1" %*
exit /b %ERRORLEVEL%
