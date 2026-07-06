# Project Research Summary

**Project:** YouTube Video Downloader
**Domain:** Single-purpose web application (yt-dlp wrapper)
**Researched:** 2026-07-06
**Confidence:** HIGH

## Executive Summary

This is a single-purpose YouTube video downloader web app — user pastes a URL, selects a format, downloads the file. Three research sources independently converge on the same architecture: **Python 3.12 + Flask 3.1 + yt-dlp 2026.07 + vanilla HTML/CSS/JS + ffmpeg + Deno/Node for JS challenges.** This is the proven pattern used by every mature reference implementation examined. No database, no async framework, no message queue — the entire app fits in a single Flask process with three routes.

The key architectural decision that determines everything: **should the backend handle the actual video download, or only metadata?** YouTube blocks datacenter IPs at the network level — no amount of cookie configuration or impersonation fixes this. The research strongly recommends a two-tier approach: use YouTube's free oEmbed API for metadata (never blocked, no rate limits), then either (a) serve download URLs for the browser to fetch directly (using the user's residential IP), or (b) accept that cloud-hosted backends will require a residential proxy service for actual downloads.

The single biggest risk is **yt-dlp staleness.** YouTube rotates its player JS every 1–3 weeks, and each rotation can break all downloads overnight. Auto-update to nightly builds must be built in from day 1 — this is not retrofittable. The second-biggest risk is the **datacenter IP blocking problem** — the app will work perfectly on a developer's laptop and fail completely in production on any cloud provider. Testing in a production-like environment before launch is mandatory, not optional.

## Key Findings

### Recommended Stack

**Python 3.12 + Flask 3.1 + yt-dlp Python API + vanilla frontend.** All research sources agree on this combination. Flask is preferred over FastAPI/Django because the app has ~3 routes and zero need for async, Pydantic models, ORM, or admin panels. The yt-dlp Python API (`yt_dlp.YoutubeDL` class) is preferred over subprocess for error handling, progress hooks, and security.

**Core technologies:**
- **Python 3.12+**: Application runtime — yt-dlp requires >= 3.8, Python 3.12.3 is already installed
- **Flask 3.1.3**: Web framework — lowest-overhead Python web framework, single-file app capability
- **yt-dlp >= 2026.07.04**: Video download engine — de facto standard, 1,800+ sites, active weekly releases
- **Deno >= 2.0.0**: JavaScript runtime for YouTube anti-bot challenges — sandboxed by default (Node has full FS/network access)
- **ffmpeg >= 6.0**: Media stream merging — YouTube serves video/audio separately; without ffmpeg, files are unplayable
- **gunicorn >= 23.0**: Production WSGI server — needed when deploying beyond `flask run`
- **Vanilla HTML/CSS/JS**: Frontend — no framework, no build step, no NPM for a single-input form

**Security-critical constraints:**
- NEVER use `subprocess` with `shell=True` — always use the Python API
- Hardcode `outtmpl` — never interpolate user input into file paths
- Restrict yt-dlp to YouTube only (`--ies youtube`)
- Pin yt-dlp version with auto-update to nightly builds
- Use `/tmp` for downloads (RAM-based, auto-cleaned)

### Expected Features

**Must have (table stakes):** Users expect paste-a-URL → see download options → select quality → get MP4. Missing any of these makes the product feel broken.
- Paste URL → auto-fetch metadata (title, thumbnail, duration)
- Quality/resolution selection (360p, 480p, 720p, 1080p)
- MP4 format download
- Error handling: invalid URL, unavailable video, age-restricted content
- Mobile-friendly responsive UI
- No registration required, free to use
- Clean, ad-free interface (this is also the primary differentiator)

**Should have (competitive differentiators):**
- **No ads, no popups, no redirects** — single biggest UX win vs competitors (Y2Mate, YT1s, SaveFrom are ad-infested)
- Real-time download progress (percentage/speed/ETA via yt-dlp progress hooks)
- File size indicator before download
- Auto-fetch on paste (debounced, no "Convert" button needed)

**Defer (v2+):**
- MP3/audio extraction (per PROJECT.md — v2 consideration)
- Dark mode (low effort but not MVP-blocking)
- Download queue (sequential queue for stacking URLs)
- Subtitle download, format conversion, bookmarklet

**Anti-features (explicitly NOT building):**
- User accounts / authentication — no login system, no session state
- Playlist/channel downloads — single video only
- Batch/multiple URL upload
- Built-in video player — serve the file, user plays locally
- Cloud storage integration

### Architecture Approach

**Single Flask process, synchronous request-response, three routes.** The app has no database, no message queue, no async. Every download gets its own temp directory, and a background cleanup thread deletes old files. This is the canonical pattern from every mature Flask+yt-dlp reference.

**Major components:**
1. **Flask Routes (app.py)** — 3 routes: `GET /` (serve SPA), `POST /info` (metadata), `POST /download` (file). URL validation, orchestration.
2. **yt-dlp Layer** — `yt_dlp.YoutubeDL()` Python API for metadata extraction (`extract_info(url, download=False)`) and file download. Progress hooks for real-time feedback.
3. **Temp Filesystem** — `tempfile.mkdtemp(prefix='yt-dlp-')` per download. Files streamed to user via `send_file()`, then cleaned by background sweeper.
4. **Cleanup Thread** — Daemon thread deleting temp files older than 10 minutes. Runs every 5 minutes.
5. **Frontend (SPA)** — Single HTML file with inline CSS/JS. Paste URL, select format, trigger download, show progress.

### Critical Pitfalls

1. **Stale yt-dlp version** — YouTube rotates player JS every 1–3 weeks. Without auto-update to nightly builds, all downloads fail silently. Build auto-update into Phase 1.
2. **Datacenter IP blocking** — YouTube blocks cloud IPs (AWS, GCP, Azure, etc.) at the network level. The app works on a laptop but fails in production. Mitigation: use oEmbed for metadata (never blocked), serve download URLs for browser-side fetching, or use residential proxies. This is an architecture decision that must be made in Phase 1 — changing it later is a rewrite.
3. **Command injection via URL** — Using `subprocess` with `shell=True` and user-controlled URLs enables RCE. Prevention: use yt-dlp's Python API (sanitizes internally), validate URL domains, never interpolate user input into shell commands.
4. **Memory buffering for large files** — A 4K video (2–8 GB) loaded entirely into memory crashes the server. Prevention: write to temp disk, stream to user in 8 KB chunks via `stream_with_context`.
5. **No rate-limiting / request serialization** — 2–3 concurrent requests from a datacenter IP trigger HTTP 429. Prevention: serialize download requests (max concurrency 1), use `--sleep-requests 2`, cache metadata via oEmbed.
6. **Missing ffmpeg** — Without ffmpeg, YouTube downloads produce files with no audio track. ffmpeg is a hard requirement, not optional.
7. **No file cleanup** — Without a cleanup sweep, temp files accumulate indefinitely and fill the disk. Background cleanup must exist from day 1.

## Implications for Roadmap

### Phase 1: Foundation (Infrastructure & Architecture)
**Rationale:** This phase establishes the architectural decisions that every subsequent phase depends on. Security, streaming, cleanup, and auto-update cannot be retrofitted.

**Delivers:**
- Flask skeleton with 3 routes stubbed
- yt-dlp Python API integration with auto-update to nightly builds
- Temp directory management (`tempfile.mkdtemp`) with background cleanup thread
- Streaming file serving (8 KB chunks, not buffered in memory)
- ffmpeg/Deno availability verification on startup
- URL validation + YouTube-only extractor restriction
- oEmbed API integration for metadata caching

**Addresses features:** URL validation, error handling infrastructure, clean ad-free interface (inherent in architecture)

**Avoids pitfalls:**
- ✅ Pitfall 1 (stale yt-dlp) — auto-update to nightly from day 1
- ✅ Pitfall 3 (command injection) — Python API, no subprocess
- ✅ Pitfall 4 (memory buffering) — streaming architecture, not buffering
- ✅ Pitfall 6 (missing ffmpeg) — startup verification
- ✅ Pitfall 7 (no cleanup) — background cleanup thread
- ✅ Pitfall 11 (metadata sanitization) — `--restrict-filenames`, hardcoded outtmpl
- ✅ Pitfall 13 (non-YouTube URLs) — extractor restriction
- ✅ Pitfall 17 (dev/prod divergence) — Docker-based dev matching prod

**Research flag:** Needs deeper research into the oEmbed API integration pattern and the streaming response implementation for large files. Otherwise well-documented.

### Phase 2: Core Backend (Metadata + Download API)
**Rationale:** This phase builds the actual download functionality on top of the Phase 1 foundation. The /info and /download routes are the heart of the app.

**Delivers:**
- `POST /info` — metadata extraction via oEmbed (primary) + yt-dlp (fallback for format details)
- `POST /download` — yt-dlp download with selected format_id, streaming response
- Format filtering and deduplication (curated 360p/480p/720p/1080p options)
- yt-dlp progress hooks integrated into the response pipeline
- Download queue (semaphore-based serialization, max concurrency 1)
- Cookie/impersonation configuration for yt-dlp
- Error handling: DRM, private videos, rate limits, network failures mapped to user-facing messages
- Rate limiting: `--sleep-requests 2`, `--sleep-interval 5`, exponential retry backoff

**Uses stack elements:** yt-dlp Python API with `extract_info` and `YoutubeDL.download`, Flask streaming, gunicorn worker tuning

**Addresses features:** Paste URL → see options, quality selection, download execution, file delivery, error handling, file size indicator

**Avoids pitfalls:**
- ✅ Pitfall 2 (datacenter IP blocking) — oEmbed for metadata, format options from cached yt-dlp call
- ✅ Pitfall 5 (rate limiting) — serialized queue, sleep intervals, exponential backoff
- ✅ Pitfall 8 (progress buffering) — Python API progress_hooks
- ✅ Pitfall 9 (impersonate/cookies) — built in at backend layer
- ✅ Pitfall 10 (request blocking) — streaming responses, gunicorn worker management
- ✅ Pitfall 12 (oEmbed caching) — metadata caching to reduce yt-dlp calls
- ✅ Pitfall 14 (DRM handling) — error mapping for playability_status
- ✅ Pitfall 15 (format selection) — curated format list, not raw yt-dlp format strings

**Research flag:** Needs deeper research on (a) the exact oEmbed API response shape and caching strategy, (b) yt-dlp progress_hooks in a Flask streaming context, and (c) cookie management for server-side yt-dlp (cookie export workflow).

### Phase 3: Frontend (User Interface)
**Rationale:** The frontend is driven by the backend JSON response shapes established in Phase 2. Building the UI before the API is available means working against guessed data shapes.

**Delivers:**
- Single HTML page with centered URL input, debounced auto-fetch
- Video preview card (thumbnail, title, duration, channel)
- Format/quality selection (radio buttons or dropdown with file sizes)
- Download trigger button with real-time progress bar (percentage, speed, ETA)
- Error display with specific user-facing messages
- Mobile-responsive CSS (works on phone screens)
- Dark mode support (`prefers-color-scheme`)
- Download queue indicator (sequential processing)

**Uses stack elements:** Vanilla HTML/CSS/JS — no frameworks, no build step

**Addresses features:** Mobile-friendly UI, video preview, quality selection, download progress, error handling, dark mode, download queue, auto-fetch

**Addresses differentiators:** D1 (ad-free), D2 (real-time progress), D3 (video preview), D4 (file size), D5 (dark mode), D6 (download queue), D7 (auto-fetch)

**Avoids pitfalls:**
- ✅ Pitfall 8 (silent downloads) — progress bar driven by backend hooks

**Research flag:** No deep research needed — standard patterns for a single-page form with fetch API calls. Skip research-phase.

### Phase 4: Polish & Production Hardening
**Rationale:** All core functionality is built and tested by this point. Polish focuses on edge cases, deployment, and documentation.

**Delivers:**
- Dockerfile for reproducible deployment
- Error message refinement (test all error paths with real YouTube URLs)
- Startup health checks (yt-dlp works, ffmpeg works, YouTube extraction works)
- Documentation: README with setup instructions, cookie export guide
- Bookmarklet (optional convenience)
- Performance tuning: gunicorn worker count, timeout settings, disk monitoring

**Addresses features:** Polish of all MVP features, production readiness

**Avoids pitfalls:**
- ✅ Pitfall 2 (datacenter IP) — production testing with staged environment
- ✅ Pitfall 17 (dev/prod divergence) — Docker-based parity

**Research flag:** Docker image composition needs standard patterns research — well-documented. Skip research-phase.

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** The architecture for streaming, cleanup, auto-update, and security must exist before any download logic is built. These cannot be retrofitted — changing from buffer to stream or adding auto-update after launch is a rewrite.
- **Phase 2 before Phase 3:** The frontend displays data whose shape is determined by the backend API. Building the UI without knowing the exact JSON response structure leads to rework. The API must be stable first.
- **Phase 3 before Phase 4:** Polish (Docker, documentation, edge cases) applies to a finished product. There is no point wrapping a half-built app in a Docker container.
- **Security is not a phase:** Command injection prevention, URL validation, and metadata sanitization are built into Phase 1 and maintained across all phases. They are architectural constraints, not bolt-on features.
- **The datacenter IP problem affects every phase:** Phase 1 must decide the download architecture (server-side vs browser-side fetching). Phase 2 implements it. Phase 3 designs the UI around it. Phase 4 tests it in production. This is not a Phase 4 problem.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2:** oEmbed API integration pattern (response shape, caching TTL), yt-dlp progress_hooks + Flask streaming integration, server-side cookie management workflow

Phases with standard patterns (skip research-phase):
- **Phase 3:** Single-form vanilla frontend — well-established patterns, no research needed
- **Phase 4:** Dockerfile + documentation — standard patterns, no research needed

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python + Flask + yt-dlp is a proven combination verified against multiple working reference implementations. Version recommendations verified against official release pages and current system state. |
| Features | HIGH | The feature landscape for YouTube downloaders is well-established and has not shifted significantly in 2+ years. Competitor analysis covers all major players. oEmbed API patterns are documented by Google. |
| Architecture | HIGH | Single Flask process with three routes is the canonical pattern from every mature reference examined. Architecture is simple enough that there is little room for wrong choices. |
| Pitfalls | HIGH | Based on official yt-dlp CVE database, GitHub issue tracker, production post-mortems, and community documentation. The pitfall landscape is well-documented and actively maintained. |

**Overall confidence:** HIGH — The research converges on a well-established pattern with clear, documented risks. No areas of significant disagreement were found across research sources.

### Gaps to Address

- **Datacenter IP blocking mitigation:** The research clearly identifies the problem but the exact mitigation strategy (browser-side download URLs vs residential proxy vs home server deployment) needs to be decided during Phase 1 planning. This is a project-specific deployment decision, not a research gap.
- **oEmbed API exact response shape for YouTube in 2026:** The oEmbed API is well-documented but the exact fields returned for YouTube videos (especially duration and format availability) should be verified with a live API call during Phase 2 planning.
- **Progress hooks + Flask streaming integration:** The combination of yt-dlp's `progress_hooks` callback with Flask's `stream_with_context` and `Response` generator is documented by separate sources but the exact integration pattern should be validated with a proof-of-concept in Phase 2.
- **Node.js upgrade requirement:** Current system has Node v21.7.3 (below the v22 floor for yt-dlp's JS runtime). Deno is the recommended option but is not installed. This dependency needs to be resolved in Phase 1 setup — either install Deno or upgrade Node.

## Sources

### Primary (HIGH confidence)
- [yt-dlp GitHub release v2026.07.04](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.07.04) — Current version, Python recommendation
- [yt-dlp Python API documentation](https://yt-dlp-yt-dlp.mintlify.app/advanced/embedding) — Python API patterns, progress hooks
- [yt-dlp EJS announcement](https://github.com/yt-dlp/yt-dlp/issues/15012) — JS runtime requirement for YouTube
- [yt-dlp security advisories](https://github.com/yt-dlp/yt-dlp/security/advisories) — CVE details, security requirements
- [yt-dlp changelog](https://github.com/yt-dlp/yt-dlp/blob/HEAD/Changelog.md) — CVE history, breaking changes
- [Flask 3.1.3 release](https://pypi.org/project/Flask/) — Current Flask version
- [Flask streaming documentation](https://flask.palletsprojects.com/en/latest/patterns/streaming/) — File streaming pattern
- [Google oEmbed API](https://www.youtube.com/oembed?url=...) — Free, never rate-limited metadata API
- [yt-dlp troubleshooting & FAQ](https://yt-dlp-yt-dlp.mintlify.app/reference/troubleshooting) — Official troubleshooting guide
- [Python subprocess PIPE deadlock warning](https://docs.python.org/3/library/subprocess.html) — Memory buffering anti-pattern

### Secondary (MEDIUM confidence)
- [oliverjueguen/yt-downloader](https://github.com/oliverjueguen/yt-downloader) — Reference Flask+yt-dlp architecture
- [abhint/youtube-downloader](https://github.com/abhint/youtube-downloader) — Multi-file organization pattern
- [UndercoverComputing/yt-dlp](https://github.com/UndercoverComputing/yt-dlp) — Temp file cleanup mechanism
- [ydl_api_ng project](https://unsubbed.co/tools/ydl-api-ng/) — Reference Flask+yt-dlp architecture
- [DEV blog: Flask+yt-dlp frontend](https://dev.to/john_jewskiz/i-built-a-free-yt-dlp-web-frontend-that-supports-1000-sites-heres-how-1f45) — Rate limiting, /tmp strategy, pitfalls
- [yt-dlp wiki: EJS setup](https://deepwiki.com/yt-dlp/yt-dlp-wiki/3.3-external-javascript-(ejs)-setup) — JS runtime comparison
- [CRtheHILLS/yt-dlp-rescue](https://github.com/CRtheHILLS/yt-dlp-rescue) — Production anti-bot guide
- [VidPickr failure analysis](https://vidpickr.com/blog/why-youtube-downloads-fail-2026-data) — Production failure patterns
- [VidPickr anti-bot evolution](https://vidpickr.com/blog/youtube-anti-bot-evolution-2026) — YouTube anti-bot changes
- [DEV post on IP trafficking](https://dev.to/osovsky/i-was-building-a-cloud-video-service-youtube-turned-me-into-an-ip-trafficker-1l9o) — Datacenter IP blocking
- [Stack Overflow: Flask send_file with temp files](https://stackoverflow.com/questions/69869204/flask-send-file-with-temporary-files) — Correct temp file serving pattern
- [Competitor analysis: Y2Mate, YT1s, SaveFrom, Y2meta, VidsSave](https://) — Market context, feature baseline
- Self-hosted open-source projects: MeTube (14k ⭐), yt-dlp-web-ui (2.5k ⭐), yt-webui

### CVEs and Security Advisories
- CVE-2026-26331 — `--netrc-cmd` command injection (RCE via malicious URL + HTTP redirect)
- CVE-2026-50574 — aria2c manifest injection (arbitrary file write → RCE)
- CVE-2026-50019 — Cookie leak with curl downloader
- CVE-2026-50023 — Filename sanitization bypass (arbitrary file write)
- CVE-2025-54072 — `--exec` option injection (RCE via malicious metadata)
- GHSA-f7j3-774f-rfhj — curl cookie leak
- GHSA-c6mh-fpjc-4pr3 — filename sanitization bypass
- GHSA-79w7-vh3h-8g4j — additional security advisory

---
*Research completed: 2026-07-06*
*Ready for roadmap: yes*
