@echo off
REM ===================================================================
REM  Build script for YouTube Video Downloader (Windows)
REM  Creates dist/youtube-downloader.exe
REM ===================================================================
REM  Prerequisites:
REM    1. Python 3.10+ installed (python --version)
REM    2. pip install -r requirements-build.txt
REM    3. This script must be run from the project root
REM       (the directory containing app.py)
REM ===================================================================

setlocal enabledelayedexpansion

echo [1/4] Checking Python...
python --version >nul 2>&1 || (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    exit /b 1
)

echo [2/4] Installing build requirements...
pip install -r requirements-build.txt
if errorlevel 1 (
    echo ERROR: Failed to install build requirements
    exit /b 1
)

echo [3/4] Running PyInstaller...
pyinstaller youtube-downloader.spec --noconfirm --clean
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo [4/4] Build complete!
echo.
echo   Output: dist\youtube-downloader.exe
echo.
echo   To run on this or another Windows machine:
echo     1. Copy dist\youtube-downloader.exe to the target machine
echo     2. Ensure ffmpeg.exe is on PATH (download from ffmpeg.org)
echo     3. Double-click youtube-downloader.exe
echo     4. Open http://localhost:5000 in your browser
echo.
echo   Note: yt-dlp auto-updates on first launch (needs internet).

endlocal
