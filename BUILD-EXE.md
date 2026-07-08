# YouTube Video Downloader — Windows .exe Build

This document explains how to package the YouTube Video Downloader Flask app
into a standalone `youtube-downloader.exe` that can run on any Windows machine
without Python installed.

---

## Prerequisites (on the build machine)

1. **Windows 10/11** with Python 3.10+
   - Download from https://www.python.org/downloads/windows/
   - During install, check **"Add Python to PATH"**

2. **Project files**: `app.py`, `templates/`, `youtube-downloader.spec`,
   `requirements.txt`, `requirements-build.txt`

---

## Step 1 — Install build dependencies

```powershell
pip install -r requirements-build.txt
```

This installs **PyInstaller** (the tool that bundles Python apps into .exe).

---

## Step 2 — Build the .exe

```powershell
pyinstaller youtube-downloader.spec --noconfirm --clean
```

Or simply run the helper script:

```powershell
build.bat
```

After the build, you'll find:

```
dist\
  youtube-downloader.exe   ← this is the standalone executable
```

---

## Step 3 — Deploy to target machine

1. Copy **only** `dist/youtube-downloader.exe` to the target Windows machine.
2. Install **ffmpeg** and add it to PATH:
   - Download from https://www.gyan.dev/ffmpeg/builds/ (get the "essentials" build)
   - Extract and add the `bin/` folder to your system PATH
   - Or place `ffmpeg.exe` next to `youtube-downloader.exe`
3. Double-click `youtube-downloader.exe`
4. Open your browser to **http://localhost:5000**

> The first launch auto-updates yt-dlp (needs internet). Subsequent launches
> are faster.

---

## Notes & Limitations

| Item | Status | Notes |
|------|--------|-------|
| **Python** | Not required | Bundled inside the .exe |
| **Flask / yt-dlp** | Bundled | Inside the .exe |
| **templates/** | Bundled | Embedded via PyInstaller `datas` |
| **ffmpeg** | External | Must be on PATH or next to .exe |
| **Deno** | Optional | yt-dlp falls back to bundled JS runtime |
| **Internet** | Required | yt-dlp auto-update + actual downloads |

### Why we don't bundle ffmpeg

ffmpeg is a large external binary (~70MB) with its own license (LGPL/GPL).
Bundling it would bloat the .exe and complicate licensing. Instead, the app
detects ffmpeg at startup and warns if missing (non-fatal — plain downloads
still work without it).

### Troubleshooting

- **"Failed to extract" / _MEIPASS errors**: Run as Administrator once, or
  ensure the .exe has write access to its folder.
- **Blank page on http://localhost:5000**: Check the console window for errors.
  Likely ffmpeg missing or no internet for the first yt-dlp update.
- **Antivirus flags the .exe**: PyInstaller binaries are sometimes flagged by
  heuristic scanners. Add an exception or code-sign the binary.

### Code signing (optional, for distribution)

```powershell
signtool sign /f your-cert.pfx /p password /t http://timestamp.digicert.com dist\youtube-downloader.exe
```
