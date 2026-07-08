---
phase: 02-core-backend-api
plan: 01
subsystem: api
tags:
  - flask
  - yt-dlp
  - video-download
  - youtube
  - streaming
  - json-api

# Dependency graph
requires:
  - phase: 01-foundation-infrastructure
    provides: Flask skeleton patterns, yt-dlp integration approach, streaming architecture, security guardrails
provides:
  - POST /info endpoint — video metadata and format listing
  - POST /download endpoint — streaming MP4 download
  - Comprehensive JSON error handling (400/404/500/429/405)
  - yt-dlp exception mapping to user-friendly error messages
affects:
  - 03-frontend-ui (consumes /info and /download endpoints)

# Tech tracking
tech-stack:
  added:
    - flask 3.1.3
    - yt-dlp 2026.07.04
  patterns:
    - Single-file Flask application (D-01)
    - yt-dlp Python API with nightly auto-update (D-02, D-03)
    - Streaming file download via generator (D-04, D-05, CHUNK_SIZE=8192)
    - Per-request temp directories with cleanup daemon (D-06, D-07)
    - URL validation regex for youtube.com/watch?v= / youtu.be/ (D-08)
    - Hardcoded outtmpl for path traversal prevention (D-09)
    - Extractor restriction to [youtube] only (D-10)
    - Global Flask error handlers returning structured JSON (D-13)
    - yt-dlp exception mapping to user-friendly messages (D-14)

key-files:
  created:
    - app.py — Full Flask backend with /info, /download, error handling, foundation
  modified: []

key-decisions:
  - "Single app.py structure for MVP (D-01) — no blueprints/packages until needed"
  - "yt-dlp Python API (YoutubeDL class) instead of subprocess — safer, avoids shell injection (D-02)"
  - "Streaming via generator with Response() and CHUNK_SIZE=8192 — Flask 3.x send_file does not accept chunksize"
  - "Hardcoded outtmpl template prevents path traversal from user input (D-09)"
  - "Format validation against yt-dlp available formats before download (T-02-02 mitigation)"
  - "HTTPException catch-all converts Flask default HTML errors (405 etc.) to structured JSON"

patterns-established:
  - "Error handling: AppError base exception class → Flask errorhandler chain → consistent JSON shape"
  - "Download lifecycle: validate URL → validate format_id → create temp dir → yt-dlp download → stream via generator → cleanup temp dir on error"

requirements-completed:
  - CORE-02
  - CORE-04
  - ERR-01
  - ERR-02
  - ERR-03

# Coverage metadata
coverage:
  - id: D1
    description: POST /info returns video title, formats, duration, thumbnail for valid YouTube URL
    requirement: CORE-02
    verification:
      - kind: integration
        ref: "verified via test_client with rickroll URL: 200, title present, 31 formats, duration 213s"
        status: pass
    human_judgment: false
  - id: D2
    description: POST /download streams selected format_id as downloadable MP4
    requirement: CORE-04
    verification:
      - kind: integration
        ref: "verified via test_client: 200, Content-Type video/mp4, Content-Disposition attachment, 11.8MB body"
        status: pass
    human_judgment: false
  - id: D3
    description: Invalid YouTube URLs return structured 400 JSON error
    requirement: ERR-01
    verification:
      - kind: integration
        ref: "test_client with invalid URLs (not-a-url, youtube.com/, wrong domain) → 400 JSON with error field"
        status: pass
    human_judgment: false
  - id: D4
    description: Unavailable/deleted videos return structured 404 JSON error
    requirement: ERR-02
    verification:
      - kind: integration
        ref: "test_client with non-existent 11-char video ID → 404 JSON 'This video is unavailable or has been removed.'"
        status: pass
    human_judgment: false
  - id: D5
    description: Server errors return human-readable JSON error responses
    requirement: ERR-03
    verification:
      - kind: integration
        ref: "yt-dlp exception mapping tested for rate limiting (429), ffmpeg missing (500), generic failure (500)"
        status: pass
    human_judgment: false

# Metrics
duration: 5 min
completed: 2026-07-08
status: complete
---

# Phase 2: Core Backend API — Summary

**Flask backend with POST /info (metadata + format listing), POST /download (streaming MP4), and comprehensive JSON error handling using yt-dlp**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-08T11:16:06+0100
- **Completed:** 2026-07-08T11:21:22+0100
- **Tasks:** 3 (committed individually)
- **Files modified:** 1 (app.py)

## Accomplishments

- **POST /info endpoint** — accepts `{"url": "..."}`, validates YouTube URL, fetches video metadata via yt-dlp `extract_info(download=False)`, returns title, formats array (format_id/quality/filesize/ext/has_video/has_audio), duration, thumbnail_url. Verified with 31 formats for Rick Astley video.
- **POST /download endpoint** — accepts `{"url": "...", "format_id": "18"}`, validates both fields, validates format_id against yt-dlp's available formats (T-02-02 mitigation), downloads to isolated temp directory, streams file as attachment with proper Content-Type and Content-Disposition. Verified with 11.8MB 360p download.
- **Comprehensive JSON error handling** — every error path returns structured `{"error", "status"}` JSON. Covers: invalid URL (400), unavailable video (404), rate limiting (429), ffmpeg missing (500), missing fields (400), invalid format_id (400), 404 routes, 405 method-not-allowed, unexpected server errors (500). No HTML or stack traces in any response.
- **Foundation patterns implemented** — yt-dlp auto-update to nightly (D-03), ffmpeg detection, Deno >= 2.0.0 check (D-12), temp file cleanup daemon (D-07), URL validation (D-08), extractor restriction to [youtube] (D-10), hardcoded outtmpl (D-09), global error handlers (D-13), yt-dlp exception mapping (D-14).

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement POST /info endpoint** - `bcdf672` (feat) — Flask app foundation + /info route + error infrastructure
2. **Task 2: Implement POST /download endpoint** - `c4df31f` (feat) — /download route with streaming generator
3. **Task 3: Comprehensive JSON error handling** - `7809257` (fix) — HTTPException catch-all, all error paths verified

## Files Created/Modified

- `app.py` — Full Flask backend application (~550 lines). Contains: server setup, yt-dlp auto-update, ffmpeg/Deno checks, temp file management with cleanup daemon, URL validation (D-08), yt-dlp options helpers with hardcoded outtmpl (D-09) and extractor restriction (D-10), AppError exception class, yt-dlp error mapping (D-14), global Flask error handlers (D-13) with HTTPException catch-all, health check endpoint, POST /info endpoint, POST /download endpoint with chunked streaming (D-05).

## Decisions Made

- **Streaming via generator + Response()** — Flask 3.x `send_file()` does not accept a `chunksize` parameter. Used a generator that reads the temp file in 8192-byte chunks and wraps it in `Response()` with explicit Content-Disposition header. This satisfies D-05 (chunked streaming) and prevents memory exhaustion for large files.
- **Format validation before download** — Before downloading, the /download endpoint fetches video info and checks the requested format_id against the available formats list. This prevents T-02-02 (format_id tampering) and provides a clear error message listing available formats.
- **HTTPException catch-all** — Flask/Werkzeug returns HTML for HTTP errors not explicitly registered (405, 413, etc.). Added a generic `@app.errorhandler(HTTPException)` that converts all such errors to JSON with consistent shape, while more specific handlers (400/404/500/AppError) still take precedence.

## Deviations from Plan

None — plan executed exactly as written.

**Total deviations:** 0 auto-fixed
**Impact on plan:** None

## Issues Encountered

- Flask 3.x `send_file()` does not accept `chunksize` parameter — resolved by switching to `Response()` with a generator that reads in 8192-byte chunks. The streaming behavior is equivalent.

## Threat Surface Scan

No new threat surface beyond what was documented in the plan's `<threat_model>`.

## Next Phase Readiness

- All Phase 2 API endpoints implemented and verified
- Ready for Phase 3 (Frontend User Interface) which consumes `/info` and `/download`
- Phase 3 should implement: URL input field, video preview with thumbnail, format selection dropdown, download button with progress indicator, error display for API error responses

---

*Phase: 02-core-backend-api*
*Completed: 2026-07-08*
