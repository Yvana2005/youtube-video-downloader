# YouTube Video Downloader

A Flask-based web application for downloading YouTube videos using yt-dlp. Features a single-page frontend with real-time progress tracking, format selection, and background download support.

## Features

- **Video Info Extraction** — Fetch metadata, available formats, durations, thumbnails
- **Format Selection** — Choose from video+audio, video-only, audio-only streams
- **Real-time Progress** — Background downloads with progress tracking (speed, ETA, %)
- **Secure** — URL validation, extractor restrictions, isolated temp directories
- **Cross-platform** — Runs on Linux, macOS, Windows (as `.exe` via PyInstaller)

## Quick Start

### Prerequisites

- Python 3.11+
- ffmpeg (required for merged formats)
- Deno 2.0+ (optional, for yt-dlp JS runtime)

### Installation

```bash
git clone https://github.com/Yvana2005/youtube-video-downloader.git
cd youtube-video-downloader
pip install -r requirements.txt
```

### Run Development Server

```bash
python app.py
```

Open http://localhost:5000 in your browser.

### Build Windows Executable

```bash
pip install -r requirements-build.txt
pyinstaller youtube-downloader.spec
```

The `.exe` will be in `dist/youtube-video-downloader.exe`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Frontend SPA |
| POST | `/info` | Get video metadata & formats |
| POST | `/download` | Download & stream video |
| POST | `/download/start` | Start async background download |
| GET | `/download/progress/<id>` | Check download progress |
| GET | `/download/result/<id>` | Get completed download |

### Example: Get Video Info

```bash
curl -X POST http://localhost:5000/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### Example: Download Video

```bash
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "format_id": "18"}' \
  --output video.mp4
```

## Project Structure

```
.
├── app.py                    # Flask backend (single file)
├── requirements.txt          # Python dependencies
├── requirements-build.txt    # Build dependencies (PyInstaller)
├── youtube-downloader.spec   # PyInstaller spec
├── build.bat                 # Windows build script
├── templates/
│   └── index.html           # Frontend SPA
├── .github/workflows/ci.yml # GitHub Actions CI
└── .planning/               # GSD workflow artifacts
```

## Security

- Extractor restricted to YouTube only
- Hardcoded output templates (no path traversal)
- URL validation (YouTube domains only)
- List-form arguments only (no shell injection)
- Temp directories auto-cleaned (10 min TTL)

## License

MIT License — see [LICENSE](LICENSE) for details.