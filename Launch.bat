@echo off
setlocal
title Doom Downloader
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto dependencies

echo Creating environment...
where py >nul 2>&1
if errorlevel 1 (
    python -m venv .venv
) else (
    py -3 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo Python 3.11 or newer is required.
    pause
    exit /b 1
)

:dependencies
if exist ".venv\.doom-setup" goto launch
echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Setup failed. Check your connection and run Launch.bat again.
    pause
    exit /b 1
)
type nul > ".venv\.doom-setup"

:launch
start "" ".venv\Scripts\pythonw.exe" main.py
if errorlevel 1 (
    ".venv\Scripts\python.exe" main.py
    pause
)
exit /b 0
