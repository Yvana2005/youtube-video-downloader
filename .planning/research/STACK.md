# Technology Stack

**Project:** YouTube Video Downloader
**Researched:** 2026-07-06
**Mode:** Ecosystem (Stack dimension)

## Executive Stack Decision

**Python 3.12 + Flask 3.1 + yt-dlp 2026.07 + vanilla HTML/CSS/JS + Deno/Node for JS challenges + ffmpeg**

Minimal dependencies. Maximum compatibility. Zero framework overhead.

---

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ (3.12.3 on current system) | Application runtime | yt-dlp requires >= 3.8, recommends >= 3.11. Python 3.12.3 is installed and well above the floor. No need to chase 3.14. |
| Flask | 3.1.3 (2026-02-18) | Web framework | Lowest-overhead Python web framework. Single file app. No ORM, no auth system, no boilerplate. Requires Python >= 3.9 — satisfied. |
| yt-dlp | 2026.07.04 | Video download engine | The de facto standard. Actively maintained (weekly releases). Supports 1,800+ sites. Python API allows embedding without subprocess. |

### JavaScript Runtime (Required for YouTube)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Deno | >= 2.0.0 | YouTube JS challenge solving | **Recommended.** yt-dlp now requires an external JS runtime for full YouTube support (since 2025.11.12). Deno is the only runtime enabled by default. It runs with restricted permissions (no FS/network access when called by yt-dlp), making it the most secure option. |
| yt-dlp-ejs | 0.8.0 | EJS challenge solver scripts | Required dependency of yt-dlp (auto-installed with pip). Contains the JS logic to solve YouTube's anti-bot challenges. |

**Fallback:** Node.js >= 22.0.0 (current system has Node v21.7.3 which is below the upcoming minimum of v22). If Deno cannot be installed, upgrade Node to v22+ and pass `--js-runtimes node` to yt-dlp.

**Warning:** Without a JS runtime, YouTube downloads will have severely limited format availability and will eventually break entirely. This is not optional — it is a hard requirement.

### System Dependencies

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ffmpeg | >= 6.0 (6.1.1 on current system) | Media stream merging | YouTube serves video and audio as separate streams. yt-dlp needs ffmpeg to merge them into a single MP4. Without ffmpeg, most YouTube downloads will fail or produce separate files. |

### Frontend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| HTML | — | Page structure | No build step, no framework, no NPM. |
| CSS | — | Styling | Vanilla. One stylesheet. Minimalist UI. |
| JavaScript | — | UX interactions | Vanilla. Format selection, download trigger, progress display. No SPA framework needed for a single-purpose page. |

### Python Libraries (pip)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `flask` | >= 3.1.3 | Web framework | Every request handler |
| `yt-dlp` | >= 2026.07.04 | Video download engine | Core download/format-listing logic |
| `yt-dlp-ejs` | >= 0.8.0 | YouTube JS challenge support | Auto-installed with yt-dlp |
| `gunicorn` | >= 23.0 | Production WSGI server | When deploying beyond development (`flask run`) |

---

## Alternatives Considered (and Rejected)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | Flask 3.1 | FastAPI | FastAPI adds Pydantic dependency, async overhead, and OpenAPI generation. This app has ~3 routes. Flask's simplicity is a better fit. |
| Web framework | Flask 3.1 | Django | Insane overkill for a single-page app. Django requires project structure, ORM, admin, auth — none of which are needed. |
| Download engine | yt-dlp | youtube-dl (legacy) | youtube-dl is effectively unmaintained (last release 2021). yt-dlp is the active fork with all YouTube compatibility fixes. |
| Download engine | yt-dlp (Python API) | subprocess + yt-dlp CLI | Subprocess is fragile — error handling requires parsing stderr, progress tracking is harder, and you lose type safety. The Python API (`YoutubeDL` class) is the correct approach. |
| Frontend | Vanilla JS | React / Vue / Svelte | A single form with a URL input and download button does not need a virtual DOM. Adding a framework introduces a build step, NPM dependencies, and bundle overhead for zero benefit. |
| JS runtime | Deno | Node.js | Node.js has full FS/network access by default when called by yt-dlp — a security concern. Deno is sandboxed by default. Also Deno is enabled by default; Node requires `--js-runtimes node` flag. |
| Production server | gunicorn | uWSGI / hypercorn | gunicorn is the simplest WSGI server. uWSGI is overly complex. hypercorn is for ASGI (async) which Flask doesn't need. |
| Temp storage | `/tmp` (RAM) | Persistent directory on disk | RAM-based temp storage auto-clears on reboot. No cleanup cron jobs needed. Disk-based storage risks filling the drive and requires a cleanup mechanism. |

---

## Installation

### System Dependencies

```bash
# ffmpeg (if not already installed)
sudo apt install ffmpeg

# Deno (recommended JS runtime for YouTube support)
curl -fsSL https://deno.land/install.sh | sh
# Ensure ~/.deno/bin is in your PATH

# Or if using Node.js (minimum v22):
# Current system has v21.7.3 — upgrade required
# npm install -g n && n lts
```

### Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install
pip install flask>=3.1.3 yt-dlp>=2026.07.04

# For production
pip install gunicorn>=23.0
```

### Verify Installation

```bash
python3 -c "
from yt_dlp import YoutubeDL
from flask import Flask
print('yt-dlp OK')
print('Flask OK')
"

# Verify JS runtime is detected
yt-dlp --verbose 2>&1 | grep "JS runtimes"
# Should show: [debug] JS runtimes: deno-2.x.x
```

---

## Configuration Reference

### yt-dlp Options for Web Context

These are the critical options when embedding yt-dlp in a Flask app:

```python
ydl_opts = {
    # Format: best video+audio that merges cleanly
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',

    # Output: title + id + ext (prevents path traversal — SECURITY CRITICAL)
    'outtmpl': '%(title)s [%(id)s].%(ext)s',

    # Security
    'restrictfilenames': True,      # Remove special chars from filenames
    'no_warnings': True,            # Suppress console warnings
    'quiet': True,                  # Suppress console output (web app, not CLI)
    'ignoreerrors': True,           # Don't crash on single-video errors

    # Network
    'socket_timeout': 30,           # Abort slow connections
    'retries': 3,                   # Retry on transient failures
    'fragment_retries': 3,          # Retry fragments

    # YouTube-specific
    'extractor_args': {'youtube': {'skip': ['hls', 'dash']}},  # Avoid fragmented formats
    'impersonate': True,            # Required for YouTube (uses JS runtime)
}
```

### Flask Streaming Pattern

```python
from flask import Flask, Response, stream_with_context

@app.route('/download')
def download():
    # ... extract info, prepare file ...

    def generate():
        # Stream file in chunks — never load entire file into memory
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                yield chunk

    return Response(
        stream_with_context(generate()),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'video/mp4',
        }
    )
```

---

## Version Compatibility Matrix

| Dependency | Minimum | Recommended | Verified |
|------------|---------|-------------|----------|
| Python | 3.8 | 3.12+ | ✅ 3.12.3 |
| Flask | 3.0 | 3.1.3 | ✅ |
| yt-dlp | 2026.06.09 (security fix) | 2026.07.04 | ✅ |
| yt-dlp-ejs | 0.8.0 | 0.8.0 | ✅ (auto with yt-dlp) |
| Deno | 2.0.0 | latest | ⚠️ Not installed |
| Node.js | 22.0.0 | latest LTS | ⚠️ v21.7.3 (too old) |
| ffmpeg | 4.0 | 6.1+ | ✅ 6.1.1 |
| gunicorn | 20.0 | 23.0+ | Not installed |

---

## What NOT to Use

| Technology | Reason |
|-----------|--------|
| **Celery / Redis** | Overkill. Download is synchronous within a single request or a simple background thread. No queue infrastructure needed for a single-user app. |
| **SQLite / any database** | No data to persist. No user accounts. No download history required (out of scope). |
| **Docker** | Adds a containerization layer for what runs in one process on one machine. Not needed unless deploying to a platform that requires containers. |
| **aria2c** (as external downloader) | Multiple critical CVEs (CVE-2026-50574). yt-dlp 2026.06.09 removed aria2c support for fragmented formats entirely due to RCE risk. |
| **curl** (as external downloader) | Cookie leak vulnerability (GHSA-f7j3-774f-rfhj). Only fixed in 2026.06.09 with workarounds. |
| **Nginx reverse proxy** | Not needed for a single-user dev/deploy scenario. Add only if exposing to the internet with multiple concurrent users. |
| **HTTPS** | Not needed for localhost dev. Add only if deploying publicly. |

---

## Security Requirements

These are not optional for a web app wrapping yt-dlp:

1. **Use yt-dlp >= 2026.06.09** — Fixes multiple RCE and file-write CVEs (CVE-2024-38519 bypass, CVE-2026-50574, GHSA-79w7-vh3h-8g4j, GHSA-f7j3-774f-rfhj, GHSA-c6mh-fpjc-4pr3)
2. **Do not use aria2c** — Removed from yt-dlp for security reasons
3. **Always use `'outtmpl': '%(title)s [%(id)s].%(ext)s'`** — Prevents path traversal via malicious metadata
4. **Never use `--write-subs`, `--write-auto-subs`, or `--write-thumbnail`** — These were vectors for OS-shortcut file injection (fixed in 2026.06.09 but avoid unless necessary)
5. **Rate-limit requests** — Prevent resource exhaustion (3 downloads/minute/IP is a reasonable starting point)
6. **Use `/tmp` for downloads** — RAM-based, auto-cleaned, no disk persistence of attacker-controlled files
7. **Do not pass user input to `outtmpl`** — The template string itself must be hardcoded, only the filename is derived from metadata

---

## Sources

| Source | What It Provided | Confidence |
|--------|-----------------|------------|
| [yt-dlp GitHub release v2026.07.04](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.07.04) | Current version, Python 3.11 recommendation | HIGH |
| [yt-dlp embedding docs](https://yt-dlp-yt-dlp.mintlify.app/advanced/embedding) | Python API patterns | HIGH |
| [yt-dlp EJS announcement](https://github.com/yt-dlp/yt-dlp/issues/15012) | JS runtime requirement for YouTube | HIGH |
| [Flask 3.1.3 release](https://pypi.org/project/Flask/) | Current Flask version | HIGH |
| [Flask streaming docs](https://flask.palletsprojects.com/en/latest/patterns/streaming/) | File streaming pattern | HIGH |
| [yt-dlp security advisories](https://github.com/yt-dlp/yt-dlp/security/advisories) | CVE details, security requirements | HIGH |
| [ydl_api_ng project](https://unsubbed.co/tools/ydl-api-ng/) | Reference Flask+yt-dlp architecture | MEDIUM |
| [DEV blog: Flask+yt-dlp frontend](https://dev.to/john_jewskiz/i-built-a-free-yt-dlp-web-frontend-that-supports-1000-sites-heres-how-1f45) | Rate limiting, /tmp strategy, pitfalls | MEDIUM |
| [yt-dlp wiki: EJS setup](https://deepwiki.com/yt-dlp/yt-dlp-wiki/3.3-external-javascript-(ejs)-setup) | JS runtime comparison | HIGH |
| [Ubuntu 26.04 python3 package](https://packages.ubuntu.com/en/resolute/python3) | System Python version | HIGH |

---

**Confidence Assessment**

| Area | Level | Notes |
|------|-------|-------|
| Stack selection | HIGH | Flask + yt-dlp is a proven combination with multiple reference implementations |
| Version accuracy | HIGH | Verified against official release pages dated July 2026 |
| Security analysis | HIGH | Based on official yt-dlp CVEs with published fixes |
| JS runtime requirement | HIGH | Official yt-dlp announcement, non-negotiable for YouTube |
| Production readiness | MEDIUM | Gunicorn config, rate limiting, and hardening need phase-level design |
