# Architecture Patterns

**Domain:** YouTube video downloader web app
**Researched:** 2026-07-06

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (User)                               │
│                                                                     │
│  [Paste URL] → POST /info                              ┌──────────┐│
│  [Select format] → POST /download                      │ SPA:     ││
│  [Download file] ← /dl/<filename>                      │ HTML +   ││
│                                                        │ CSS + JS ││
│                                                        └────┬─────┘│
└───────────────────────────────────────────────────────────────┼─────┘
                                                                │
                                                        HTTP JSON/File
                                                                │
                                                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      Flask Backend (app.py)                           │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐     │
│  │ Route: /     │  │ Route: /info │  │ Route: /download         │     │
│  │ Serve SPA    │  │ POST: url    │  │ POST: url + format_id    │     │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘     │
│         │                 │                       │                    │
│         │                 ▼                       ▼                    │
│         │         ┌──────────────────┐  ┌──────────────────────┐      │
│         │         │ yt-dlp.extract_  │  │ yt-dlp.YoutubeDL()  │      │
│         │         │ info(url,        │  │ .download([url])    │      │
│         │         │   download=False)│  │                      │      │
│         │         │                  │  │ format=format_id    │      │
│         │         │ Returns:         │  │ outtmpl=temp path   │      │
│         │         │  • title         │  └──────────┬───────────┘      │
│         │         │  • duration      │             │                   │
│         │         │  • formats[]     │             ▼                   │
│         │         │  • thumbnail     │  ┌──────────────────────┐      │
│         │         └──────────────────┘  │ Temporary file on    │      │
│         │                               │ /tmp/ or downloads/  │      │
│         │                               └──────────┬───────────┘      │
│         │                                          │                   │
│         ▼                                          ▼                   │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │               send_file() → HTTP Response                    │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │               Cleanup Thread (background)                     │      │
│  │  Deletes temp files older than N minutes every M minutes      │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                       │
│  Required system dependency: ffmpeg (for yt-dlp merge operations)    │
└───────────────────────────────────────────────────────────────────────┘
```

### Why This Architecture

The entire application fits into a single Flask process because:

- **No database** — No user accounts, no persistent state, no sessions. Each request is stateless.
- **No message queue** — Single-user. The download happens synchronously within the HTTP request. The user waits for the file.
- **Temporary files only** — Files are written to a temp directory, streamed to the user, then deleted by a background cleanup thread.

This is the canonical pattern used by every mature Flask + yt-dlp project examined (oliverjueguen/yt-downloader, abhint/youtube-downloader, UndercoverComputing/yt-dlp, etc.).

### Alternative Considered: Async Downloads

Some implementations (e.g., vikranthsalian/yt-downloader-py) use threading with progress polling endpoints (`/progress/<video_id>`, `/result/<video_id>`). This adds complexity:
- Requires a progress-tracking data structure in memory
- Requires polling or SSE from the frontend
- Still dead-ends at the same yt-dlp call

For a single-user app where downloads are synchronous, threading is unnecessary complexity. The user pastes a URL, waits a moment, and gets the file. **Keep it synchronous.**

---

## Component Boundaries

| Component | Responsibility | Communicates With | Notes |
|-----------|---------------|-------------------|-------|
| **Flask Routes** | Handle HTTP, validate input, orchestrate flow | Frontend ↔ yt-dlp layer ↔ temp filesystem | 3-4 routes max |
| **yt-dlp Layer** | Extract metadata, download files | Flask routes ←→ system (yt-dlp Python API) | Called as Python library, not subprocess |
| **Temp Filesystem** | Hold downloaded files before serving | yt-dlp layer → Flask route → user | Use `/tmp/` or project `downloads/` dir |
| **Cleanup Thread** | Delete expired temp files | Filesystem only | Simple age-based sweep |
| **FFmpeg** | Merge video+audio streams | yt-dlp (calls it internally) | System dependency, not in Python code |
| **Frontend (SPA)** | URL input, format selection, progress feedback | User ↔ Flask routes | Single HTML file + inline CSS/JS |

### What's NOT a Component

- **No database layer** — Not needed. The app has no persistent state.
- **No auth layer** — Not needed. Single-user, local deployment.
- **No task queue** — Not needed. Synchronous download within request.
- **No caching layer** — Not needed for MVP. Adding a simple `{url: info}` dict cache is a trivial optimization but out of scope for initial build.

---

## Data Flow

### Flow 1: Get Available Formats (Phase 1)

```
User enters URL → clicks "Get Formats"
    │
    ▼
POST /info  { "url": "https://youtube.com/watch?v=..." }
    │
    ▼
Flask validates URL format (regex check)
    │
    ▼
yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
    │  ydl_opts = { "quiet": True, "no_warnings": True }
    │
    ▼
Returns info dict containing:
  ├── title (str)
  ├── duration (int, seconds)
  ├── thumbnail (str, URL)
  ├── formats (list of dicts)
  │     each: { "format_id", "ext", "resolution", 
  │             "filesize", "vcodec", "acodec", ... }
  └── ...
    │
    ▼
Flask filters formats to user-friendly list:
  ├── Remove audio-only formats (acodec only, no vcodec)
  ├── Group by resolution
  ├── Label: "1080p MP4", "720p MP4", etc.
    │
    ▼
Response: 200 JSON
{
  "title": "...",
  "duration": "...",
  "thumbnail": "...",
  "formats": [
    { "id": "137+140", "label": "1080p MP4", "ext": "mp4" },
    { "id": "136+140", "label": "720p MP4", "ext": "mp4" },
    ...
  ]
}
    │
    ▼
Frontend renders format selection UI
```

### Flow 2: Download Video (Phase 2)

```
User selects format → clicks "Download"
    │
    ▼
POST /download  { "url": "...", "format_id": "137+140" }
    │
    ▼
Flask generates output template:
  outtmpl = f"/tmp/yt-dlp-{uuid4()}/%(title)s.%(ext)s"
    │
    ▼
yt_dlp.YoutubeDL(ydl_opts).download([url])
  ydl_opts = {
    "format": "137+140",
    "outtmpl": "/tmp/yt-dlp-<uuid>/%(title)s.%(ext)s",
    "merge_output_format": "mp4",
    "quiet": True,
    "no_warnings": True
  }
    │
    ▼
yt-dlp progress callbacks fire (optional, can show progress)
    │
    ▼
On success:
  ├── Find output file in temp directory
  ├── Get filename
  │
  ▼
flask.send_file(
  filepath,
  as_attachment=True,
  download_name="Video Title.mp4",
  mimetype="video/mp4"
)
    │
    ▼
File streams to user's browser (download prompt)
    │
    ▼
Temp file remains on disk for cleanup sweep
```

### Flow 3: Error Handling

```
Invalid URL / Private video / Deleted video / Network error
    │
    ▼
yt-dlp raises DownloadError or ExtractorError
    │
    ▼
Flask catches → returns 400/404 JSON:
  { "error": "Video not found or inaccessible" }

Format mismatch / Merge failure
    │
    ▼
Flask catches → returns 400 JSON:
  { "error": "Selected format unavailable for this video" }

Timeout (large video takes too long)
    │
    ▼
Flask route timeout → 504 or browser timeout
  (Mitigation: set sensible timeout, handle gracefully)
```

---

## File Structure

```
yt-downloader/
│
├── app.py                  # Flask application: all routes + yt-dlp logic
├── requirements.txt        # flask, yt-dlp
├── downloads/              # Temp directory for downloaded files (gitignored)
├── templates/
│   └── index.html          # Single-page frontend (HTML + inline CSS/JS)
├── static/
│   └── style.css           # (Optional) extracted styles for cleanliness
└── Dockerfile              # (Optional) container definition
```

**Why a single `app.py`?** This is a ~100-line Flask application. Splitting it into `routes/`, `services/`, `models/` is ceremony without benefit. Three routes, one yt-dlp call pattern. A single file is the right abstraction level.

**Why inline CSS/JS in index.html?** The frontend is a single form and a results list. Separating into `static/app.js`, `static/style.css`, `static/vendor/...` adds file-load complexity for zero architectural value. Extract to separate files only when the frontend grows beyond ~200 lines.

---

## Patterns to Follow

### Pattern 1: Synchronous Request-Response

**What:** The entire download happens within a single HTTP request. User clicks "Download", waits for the response, receives the file.

```python
@app.route('/download', methods=['POST'])
def download():
    url = request.json['url']
    format_id = request.json['format_id']
    
    # Generate unique temp directory per download
    dl_dir = tempfile.mkdtemp(prefix='yt-dlp-')
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(dl_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        files = os.listdir(dl_dir)
        if not files:
            return {'error': 'No file produced'}, 500
        filepath = os.path.join(dl_dir, files[0])
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=files[0]
        )
    except Exception as e:
        shutil.rmtree(dl_dir, ignore_errors=True)
        return {'error': str(e)}, 400
```

**When:** Always, for this project. No async, no polling, no background jobs.

### Pattern 2: Stateless Per-Request Temp Directories

**What:** Every download gets its own temporary directory (via `tempfile.mkdtemp`). No shared state between requests. No filename collision risk.

```python
dl_dir = tempfile.mkdtemp(prefix='yt-dlp-')
try:
    # ... yt-dlp writes to dl_dir ...
    # ... send_file serves from dl_dir ...
finally:
    # Cleanup is handled by background sweeper, not here
    # (send_file uses streaming; file must exist until response completes)
    pass
```

**When:** Always. Never reuse temp directories or guess unique filenames.

### Pattern 3: Format Info Extraction Without Download

**What:** Always call `extract_info` with `download=False` first, then download with the chosen format_id.

```python
@app.route('/info', methods=['POST'])
def info():
    url = request.json['url']
    
    if not is_valid_youtube_url(url):
        return {'error': 'Invalid YouTube URL'}, 400
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        formats = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none':  # video formats only
                formats.append({
                    'format_id': f['format_id'],
                    'ext': f.get('ext', 'mp4'),
                    'resolution': f.get('resolution', 'N/A'),
                    'filesize': f.get('filesize'),
                    'label': format_label(f),
                })
        
        return {
            'title': info.get('title'),
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
            'formats': formats,
        }
    except Exception as e:
        return {'error': str(e)}, 400
```

**When:** This is the mandatory two-phase flow. Phase 1 (info) must precede Phase 2 (download).

### Pattern 4: Background Cleanup Sweep

**What:** A daemon thread periodically deletes old temp files. Simple, reliable, no cron dependency.

```python
import threading
import time
import shutil
import os

TEMP_BASE = tempfile.gettempdir()
CLEANUP_AGE = 600  # 10 minutes
CLEANUP_INTERVAL = 300  # check every 5 minutes

def cleanup_worker():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        now = time.time()
        for entry in os.listdir(TEMP_BASE):
            path = os.path.join(TEMP_BASE, entry)
            if entry.startswith('yt-dlp-') and os.path.isdir(path):
                if now - os.path.getctime(path) > CLEANUP_AGE:
                    shutil.rmtree(path, ignore_errors=True)

cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()
```

**When:** Mandatory. Without cleanup, temp files accumulate indefinitely.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using yt-dlp as a CLI Subprocess

**What:** Calling `subprocess.run(['yt-dlp', '--format', ...])` instead of using the Python API.

**Why bad:** Loss of error handling, harder to capture output, fragile to CLI syntax changes, harder to extract progress.

**Instead:** Use `yt_dlp.YoutubeDL()` Python API.

### Anti-Pattern 2: Keeping Files After Serving

**What:** Downloading to a fixed path and serving from there without cleanup.

**Why bad:** Disk fills up. Old files accumulate. Filename collisions occur.

**Instead:** Use temp directories + cleanup sweep (Pattern 2 + Pattern 4).

### Anti-Pattern 3: Blocking the Thread with a Full Queue

**What:** Using Celery/Redis/RabbitMQ to queue download tasks.

**Why bad:** Massive overengineering. This is a single-user synchronous app. Adding a message queue multiplies infrastructure complexity for zero benefit.

**Instead:** Serve the file synchronously (Pattern 1).

### Anti-Pattern 4: Storing Downloaded Files in the Application Directory

**What:** Writing downloads to `./downloads/` without cleanup.

**Why bad:** If the app is containerized or redeployed, files are lost anyway. If not, they accumulate. Using the project dir for runtime data is messy.

**Instead:** Use the OS temp directory (`/tmp/` or `tempfile.gettempdir()`).

---

## Build Order

The components have strict dependency ordering:

| Step | Component | Depends On | Provides |
|------|-----------|------------|----------|
| 1 | Flask skeleton + / route | Nothing | Server starts, serves HTML |
| 2 | Frontend template (index.html) | Step 1 | User sees a page |
| 3 | POST /info route + yt-dlp extraction | Step 1, yt-dlp | Formats list |
| 4 | Frontend format display | Step 2 + 3 | User sees available formats |
| 5 | POST /download route + yt-dlp download | Step 1, Step 3 pattern | File served to user |
| 6 | Cleanup thread | Step 5 | Disk doesn't fill up |
| 7 | Error handling refinement | Steps 3-5 | Graceful failure UX |
| 8 | Dockerfile | Steps 1-7 | Reproducible deployment |

**Phase 1 (MVP) = Steps 1-6.** Steps 7 and 8 are polish/infrastructure.

### Build Order Rationale

The /info endpoint must exist before /download because:
1. You cannot download a format without knowing the format_id
2. The format_id comes from extract_info
3. The user must choose from available formats

The frontend must be built after the /info route because:
1. The UI is driven by the JSON response shape
2. You need to know what fields are available before designing the display

The cleanup thread must exist before production use because:
1. Every download leaves a temp file
2. Without cleanup, indefinite accumulation fills disk

---

## Scalability Considerations

For this app's scope (single-user, local deployment), scalability is not a concern. However, for awareness:

| Concern | Current (Single-User) | At 10 Concurrent Users |
|---------|----------------------|----------------------|
| **Concurrent downloads** | Synchronous; user waits | Thread pool or queue needed |
| **Disk space** | Temp files cleaned after 10min | Per-user temp space grows linearly |
| **yt-dlp rate limiting** | Not an issue (1 user) | YouTube may throttle |
| **Request timeout** | Browser timeout (~2-5 min) | Need async + progress polling |

**Recommendation:** Do not optimize for multiuser until validated. Optimize only when the single-user path is proven.

---

## Sources

- [oliverjueguen/yt-downloader — Flask + yt-dlp architecture](https://github.com/oliverjueguen/yt-downloader) — Canonical simple architecture diagram
- [abhint/youtube-downloader — Flask + yt-dlp project structure](https://github.com/abhint/youtube-downloader) — Multi-file organization pattern
- [UndercoverComputing/yt-dlp — Flask downloader with cleanup](https://github.com/UndercoverComputing/yt-dlp) — Temp file cleanup mechanism
- [yt-dlp Python API documentation](https://yt-dlp-yt-dlp.mintlify.app/api/overview) — Official Python API reference
- [Stack Overflow — flask send_file with temp files](https://stackoverflow.com/questions/69869204/flask-send-file-with-temporary-files) — Correct temp file serving pattern
