# Roadmap: YouTube Video Downloader

## Overview

A single-purpose web application that lets users download YouTube videos by pasting a URL. The journey starts with building a solid backend foundation (Flask + yt-dlp infrastructure), then adds the core download API, and finally wraps it in a clean, responsive user interface.

## Phases

- [ ] **Phase 1: Foundation & Infrastructure** - Flask skeleton, yt-dlp auto-update, temp file management, streaming architecture, security guardrails
- [x] **Phase 2: Core Backend API** - Video metadata fetching, format listing, download streaming, error detection and response
- [ ] **Phase 3: Frontend User Interface** - URL input, video preview, format selection, download with progress, error display

## Phase Details

### Phase 1: Foundation & Infrastructure

**Goal**: The core application infrastructure is in place — Flask server boots, yt-dlp is integrated with auto-update, temp file management exists, streaming architecture is established, and security guardrails are set.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, ERR-04
**Success Criteria** (what must be TRUE):

  1. Running `python app.py` (or `flask run`) starts the Flask dev server that responds on localhost
  2. yt-dlp auto-updates to the latest nightly build on application startup (verified in startup logs)
  3. Temporary download files are created in isolated per-request directories under /tmp and automatically cleaned up after 10 minutes
  4. Large files are streamed in chunks (not buffered entirely in memory), verified by downloading a large test file
  5. Missing ffmpeg is detected on startup and logged as a warning

**Plans**: TBD

### Phase 2: Core Backend API

**Goal**: The backend API that powers the application is functional — can fetch video metadata from YouTube, list available formats/qualities, and stream downloads via API endpoints.
**Depends on**: Phase 1
**Requirements**: CORE-02, CORE-04, ERR-01, ERR-02, ERR-03
**Success Criteria** (what must be TRUE):

  1. POST /info with a valid YouTube URL returns JSON containing video title, available formats (each with format_id, quality label, and file size), duration, and thumbnail URL
  2. POST /download with a valid YouTube URL and selected format_id streams the video file to the client as a downloadable MP4
  3. POST requests with invalid YouTube URLs return structured JSON error responses (not HTML or stack traces)
  4. POST requests with unavailable/deleted video IDs return structured JSON error responses indicating the video is unavailable
  5. Server errors (yt-dlp failure, ffmpeg missing, rate limiting) return human-readable JSON error responses

**Plans**: 1 plan
Plans:

- [x] 02-01-PLAN.md — Implement /info and /download endpoints with error handling

### Phase 3: Frontend User Interface

**Goal**: Users can interact with the downloader through a clean, responsive web interface — paste a URL, preview video info, select quality, download with real-time progress feedback, and see clear error messages.
**Depends on**: Phase 2
**Requirements**: CORE-01, CORE-03, CORE-05
**Success Criteria** (what must be TRUE):

   1. User can paste a YouTube URL into the input field and see the video's title, thumbnail, and duration appear automatically
   2. User can select from available format/quality options (displayed with resolution and file size)
   3. User can click a Download button and receive the selected video file
   4. Download progress is shown in real-time with percentage complete, download speed, and estimated time remaining
   5. Invalid URLs and unavailable videos display clear, user-friendly error messages in the UI

**Plans**: 1 plan
Plans:

- [x] 03-01-PLAN.md — Frontend UI with video preview, format selection, download progress, and error display

**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Infrastructure | 0/0 | Not started | - |
| 2. Core Backend API | 1/1 | Complete | 2026-07-08 |
| 3. Frontend User Interface | 0/1 | Ready for execution | - |
