@echo off
setlocal enabledelayedexpansion
title Doom Downloader
cd /d "%~dp0"

:: 1. Verify Python virtual environment
if exist ".venv\Scripts\python.exe" goto dependencies

echo [Doom Downloader] Creating Python virtual environment...
where py >nul 2>&1
if errorlevel 1 (
    python -m venv .venv
) else (
    py -3 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo [Doom Downloader] Python 3.11 or newer is required. Please install Python.
    pause
    exit /b 1
)

:dependencies
if exist ".venv\.doom-setup" goto check_frontend
echo [Doom Downloader] Installing Python engine dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [Doom Downloader] Setup failed. Check your internet connection and run Launch.bat again.
    pause
    exit /b 1
)
type nul > ".venv\.doom-setup"

:check_frontend
:: Allow forcing legacy CustomTkinter GUI via command line: Launch.bat --legacy
if "%1"=="--legacy" goto launch_legacy
if "%1"=="-l" goto launch_legacy

:: 2. Launch standalone modern desktop application window
set "ELECTRON_BIN=%~dp0desktop\node_modules\electron\dist\electron.exe"
set "MAIN_CJS=%~dp0desktop\electron\main.cjs"
set "DIST_INDEX=%~dp0desktop\dist\index.html"

:: Check if desktop dependencies are missing, install if needed
if not exist "!ELECTRON_BIN!" (
    if exist "desktop\package.json" (
        where npm.cmd >nul 2>&1
        if not errorlevel 1 (
            echo [Doom Downloader] Initializing desktop dependencies...
            call npm.cmd --prefix desktop install
        )
    )
)

:: Check if UI build is missing, compile if needed
if not exist "!DIST_INDEX!" (
    if exist "desktop\package.json" (
        where npm.cmd >nul 2>&1
        if not errorlevel 1 (
            echo [Doom Downloader] Building modern frontend UI...
            call npm.cmd --prefix desktop run build
        )
    )
)

:: Launch native desktop executable directly
if exist "!ELECTRON_BIN!" (
    echo [Doom Downloader] Starting Doom Downloader desktop window...
    start "" "!ELECTRON_BIN!" "!MAIN_CJS!" %*
    exit /b 0
)

:: Fallback if Electron binary not present
echo [Doom Downloader] Modern desktop executable not found.
echo [Doom Downloader] Falling back to Python interface...

:launch_legacy
:: Fallback to legacy CustomTkinter GUI
echo [Doom Downloader] Launching legacy interface...
start "" ".venv\Scripts\pythonw.exe" main.py
if errorlevel 1 (
    ".venv\Scripts\python.exe" main.py
    pause
)
exit /b 0
