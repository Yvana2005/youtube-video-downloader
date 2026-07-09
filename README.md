# YouTube Video Downloader

A Flask-based web application for downloading YouTube videos with metadata extraction, format selection, and progress tracking.

## Features

- **Video Info Extraction** — Fetch video title, duration, thumbnail, and available formats
- **Format Selection** — Choose from multiple video/audio qualities (1080p, 720p, 480p, audio-only, etc.)
- **Direct Download** — Stream video files directly to browser
- **Async Background Download** — Start downloads and track progress via polling
- **Real-time Progress** — Live progress updates with speed, ETA, and byte counts
- **Security Hardened** — URL validation, extractor restrictions, temp file isolation, path traversal prevention

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg (required for merging video+audio formats)
- Deno 2.0+ (optional, for yt-dlp JavaScript runtime)

### Installation

```bash
# Clone the repository
git clone https://github.com/Yvana2005/youtube-video-downloader.git
cd youtube-video-downloader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run the Application

```bash
python app.py
```

The server starts at `http://localhost:5000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Serve frontend UI |
| POST | `/info` | Get video metadata and formats |
| POST | `/download` | Stream video download |
| POST | `/download/start` | Start async background download |
| GET | `/download/progress/<id>` | Check download progress |
| GET | `/download/result/<id>` | Get completed download file |

### Example Usage

```bash
# Get video info
curl -X POST http://localhost:5000/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'

# Download video (streaming)
curl -X POST http://localhost:5000/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "format_id": "18"}' \
  -o video.mp4

# Async download
curl -X POST http://localhost:5000/download/start \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "format_id": "18"}'

# Check progress
curl http://localhost:5000/download/progress/<download_id>
```

## Build Windows Executable (.exe)

```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build the executable
pyinstaller youtube-downloader.spec

# Output: dist/youtube-downloader.exe
```

Requires: PyInstaller, dependencies from `requirements-build.txt`

## Project Structure

```
youtube-video-downloader/
├── app.py                    # Main Flask application
├── requirements.txt          # Runtime dependencies
├── requirements-build.txt    # Build dependencies
├── youtube-downloader.spec   # PyInstaller spec
├── build.bat                 # Windows build script
├── templates/
│   └── index.html           # Frontend UI
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI
├── BUILD-EXE.md             # Build documentation
└── .planning/               # GSD workflow artifacts
```

## Technology Stack

- **Backend**: Flask 3.x
- **Video Processing**: yt-dlp (nightly auto-updated)
- **Frontend**: Vanilla HTML/CSS/JS (single-page)
- **Build**: PyInstaller (onefile, windowed)
- **CI**: GitHub Actions

## Security Notes

- Only YouTube extractor enabled
- Hardcoded output templates prevent path traversal
- Per-request isolated temp directories with TTL cleanup
- URL validation with strict regex matching
- No user input reaches shell commands

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Yvana2005