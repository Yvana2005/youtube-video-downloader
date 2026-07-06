# Domain Pitfalls: YouTube Video Downloader Web App

**Domain:** YouTube video downloader web application (yt-dlp wrapper)
**Researched:** 2026-07-06
**Overall confidence:** HIGH (sources: yt-dlp official docs, GitHub issues, CVE database, production post-mortems)

---

## Critical Pitfalls

Mistakes that cause complete failures, rewrites, or security incidents.

### Pitfall 1: Using Stale yt-dlp Version (YouTube Changes Every 1–3 Weeks)

**What goes wrong:** YouTube rotates its player JavaScript every 1–3 weeks. Each rotation can change the structure of the URL deciphering function, the format extraction logic, and the PoToken requirements. A stale yt-dlp version silently produces "cipher not found", "Sign in to confirm you're not a bot", or "Video unavailable" errors — all of which look like unrelated issues to the user.

**Why it happens:** The project pins yt-dlp at install time and never updates. Package-manager versions (apt, brew, pip stable) lag weeks behind nightly builds. Developers treat yt-dlp as a static dependency like any other library, but it's a moving target that must track YouTube's anti-scraping changes.

**Consequences:**
- All downloads fail silently after a YouTube player rotation
- Users blame the app, not yt-dlp
- Debugging is opaque — errors are generic (HTTP 403, "Video unavailable")
- Each failure erodes trust; users churn permanently

**Prevention:**
- Use yt-dlp nightly builds, not stable releases. The FAQ explicitly says: *"Use nightly builds for regular use. They are updated daily with latest fixes."*
- Implement an auto-update mechanism: on app startup, run `yt-dlp --update-to nightly` (or pip equivalent: `pip install -U --pre "yt-dlp[default]"`)
- Pin a minimum yt-dlp version in the Docker image and rebuild images weekly
- Monitor the yt-dlp changelog and GitHub releases for breaking YouTube changes

**Detection:**
- Monitor logs for `WARNING: [youtube]` patterns, especially "cipher not found", "HTTP Error 403", "Sign in to confirm"
- Add a health-check endpoint that tests a known-good YouTube URL and reports success/failure
- Track yt-dlp version in logs and compare with latest nightly

**Which phase should address it:** Phase 1 (Foundation) — must be built in from day 1. Auto-update logic and version pinning are not post-hoc additions.

---

### Pitfall 2: Datacenter IP Blocking (YouTube Blocks Cloud IPs at Network Level)

**What goes wrong:** YouTube blocks all requests originating from datacenter IP ranges (AWS, GCP, Azure, OVH, Linode, Hetzner, etc.) at the network level. The user sees "Sign in to confirm you're not a bot" or HTTP 429/403 errors even with valid cookies. No amount of application-layer configuration (user-agent, cookies, headers) fixes this — the IP itself is flagged.

**Why it happens:** The developer deploys on a cloud VPS or PaaS (Railway, Heroku, Fly.io) and expects it to work like a desktop. YouTube maintains IP reputation databases and automatically flags entire ASNs belonging to cloud providers. This became aggressive in 2025–2026.

**Consequences:**
- App works on local dev machine but fails in production
- Hours wasted on cookie/config changes that can never work
- Forces architecture redesign from server-side to client-side download

**Prevention:**
- **Architecture decision:** Run yt-dlp server-side only for metadata extraction (title, duration, thumbnail, formats). Use the free YouTube oEmbed API (`https://www.youtube.com/oembed?url=...`) which is never blocked and has no rate limits for metadata.
- **For actual downloads:** Either (a) stream download URLs directly to the browser (user's residential IP fetches the bytes), or (b) route traffic through a residential proxy service.
- If using cloud proxies, use `--impersonate chrome` with `curl_cffi` installed, and set up a PO Token provider (`YT_DLP_POT_PROVIDER_URL`).

**Detection:**
- On first production deploy, test with a simple yt-dlp extract on a known-good URL
- Log the `playability_status` from YouTube responses — `LOGIN_REQUIRED` without a prior login prompt is a strong indicator
- Monitor for HTTP 429 errors that persist across cookie rotation

**Which phase should address it:** Phase 1 (Architecture decision). This determines whether the backend handles downloads or just metadata. Changing this after launch is a rewrite.

---

### Pitfall 3: Command Injection via User-Controlled URL

**What goes wrong:** An attacker crafts a malicious URL containing shell metacharacters. If the app builds a yt-dlp command string and passes it to `subprocess.run(cmd, shell=True)` or similar, the attacker achieves arbitrary code execution on the server.

**Why it happens:** The developer takes a user-supplied URL string and interpolates it into a shell command like:
```python
subprocess.run(f"yt-dlp {user_url}", shell=True)  # DANGEROUS
```

**Consequences:**
- Full remote code execution on the server
- Data exfiltration, cryptominer installation, lateral movement
- CVE disclosure, reputational damage, potential legal liability

**Recent CVE history (yt-dlp itself has had multiple injection CVEs):**
| CVE | Year | Vector | Impact |
|-----|------|--------|--------|
| CVE-2026-50019 | 2026 | Cookie leak with curl downloader | Cookie theft |
| CVE-2026-50023 | 2026 | Filename sanitization bypass | Arbitrary file write |
| CVE-2026-26331 | 2026 | `--netrc-cmd` command injection | RCE via malicious URL + HTTP redirect |
| CVE-2026-50574 | 2026 | aria2c manifest injection | Arbitrary file write → RCE |
| CVE-2025-54072 | 2025 | `--exec` option injection | RCE via malicious metadata |

**Prevention:**
- **NEVER use `shell=True`** with user input. Use `subprocess.run([cmd, arg1, arg2], shell=False)` — the list form avoids shell interpretation entirely.
- If using yt-dlp's Python API (`yt_dlp.YoutubeDL`), the library handles argument sanitization internally, reducing injection surface.
- Validate the URL before passing it to yt-dlp: reject non-HTTP(S) schemes, reject URLs containing shell metacharacters at the app level (defense in depth).
- Run the worker process in a sandboxed container with no unnecessary capabilities, read-only root filesystem, and network egress only to YouTube CDNs.
- Keep yt-dlp updated (see Pitfall 1) — recent CVEs have fixes in nightly builds.

**Detection:**
- Run dependency vulnerability scanning (pip-audit, pip-licenses, Snyk, or GitHub Dependabot)
- Monitor for unusual subprocess invocations or file writes
- Check yt-dlp release notes for security advisories before each deploy

**Which phase should address it:** Phase 1 (Foundation). Security architecture is not retrofittable.

---

### Pitfall 4: Buffering Entire Download in Memory (Out-of-Memory for Large Files)

**What goes wrong:** The app downloads the video into an in-memory buffer (e.g., `io.BytesIO`, `Popen.communicate()`) before sending it to the user. A 4K YouTube video can be 2–8 GB. The server runs out of memory, crashes, or both.

**Why it happens:** Common patterns from tutorials:
- Using `Popen.communicate()` which "The data read is buffered in memory, so do not use this method if the data size is large or unlimited" (Python docs)
- Using `yt-dlp`'s Python API with `outtmpl: '-'` (stdout) and then reading all bytes
- Building the entire response in a Flask/Express buffer before sending

**Consequences:**
- OOM kills on the server for videos over a few hundred MB
- Crash during download — user gets a partial file or timeout
- No files can be served if the server runs out of memory entirely

**Prevention:**
- **Stream, don't buffer.** Have yt-dlp write directly to a temp file on disk, then stream that file to the user via chunked transfer encoding.
- If using Flask: use `Response(stream_with_context(file_iterator()), mimetype='video/mp4')` with a generator that reads and yields 8 KB chunks.
- If using Node.js: pipe the yt-dlp child process stdout directly to the HTTP response with `res.pipe()` or stream pipelines.
- Set a maximum file size and enforce it before starting the download (check `Content-Length` or estimated size from yt-dlp's format info).
- Use `--limit-rate` to avoid saturating the server's network interface.

**Detection:**
- Monitor memory usage per worker process
- Alert on memory usage exceeding 80% of container/process limit
- Track average and max download file sizes

**Which phase should address it:** Phase 1 (Foundation) — streaming architecture must be designed upfront. Refactoring from buffer-to-file to stream is a significant rewrite.

---

### Pitfall 5: No Rate-Limiting / Request Serialization (HTTP 429, IP Bans)

**What goes wrong:** When multiple users submit download requests simultaneously, the backend hits YouTube's player API with multiple parallel requests from the same IP. YouTube responds with HTTP 429 (Too Many Requests), temporarily or permanently banning the IP.

**Why it happens:** The app doesn't serialize requests to YouTube's API. Each user request spawns a yt-dlp invocation immediately. Even 2–3 concurrent requests can trigger rate limiting from a datacenter IP.

**Consequences:**
- All downloads fail with "Sign in to confirm you're not a bot"
- IP ban lasts from 1 hour to permanent
- Every user is affected, not just the ones who triggered the limit

**Prevention:**
- **Implement a download queue** with max concurrency of 1 (or 2 at most) to YouTube's API. This is a semaphore, not a user-facing queue — queue depth is 1.
- Add mandatory sleep intervals: `--sleep-requests 2` (2 seconds between extract requests), `--sleep-interval 5` (5 seconds between downloads).
- Cache video metadata (title, formats, thumbnails) with a TTL of 10+ minutes. The oEmbed API is free and unlimited for metadata — use it instead of yt-dlp for the initial info fetch.
- Use `--retry-sleep` with exponential backoff: `--retry-sleep extractor:exp=1:20` starts at 1s, doubles to 20s max.
- Consider a per-IP user-side rate limit to prevent a single user from flooding the queue.

**Detection:**
- Log all HTTP status codes from YouTube responses
- Track 429 counts per hour per IP
- Alert when 429s exceed a threshold

**Which phase should address it:** Phase 2 (Core Backend) — but metadata caching (oEmbed) should be Phase 1. Queue architecture is a Phase 2 design decision.

---

### Pitfall 6: Missing or Wrong ffmpeg (Silent Post-Processing Failures)

**What goes wrong:** yt-dlp often downloads video and audio as separate streams (bestvideo + bestaudio) and requires ffmpeg to merge them. Without ffmpeg, the user gets either a video-only file (no audio) or a raw stream that won't play. Errors are cryptic: "Postprocessing failed", "ffprobe not found", or simply a broken output file.

**Why it happens:** The developer assumes yt-dlp produces playable files without ffmpeg. The Docker image doesn't include ffmpeg. The system PATH doesn't include ffmpeg. A minimal install of ffmpeg is missing codec support (e.g., no libvpx-vp9, no libmp3lame).

**Consequences:**
- Downloaded files are unplayable (no audio track)
- Users blame the app
- Hours of debugging "why is my file broken?"

**Prevention:**
- **Always install ffmpeg** as a hard dependency — not optional, not recommended, but required.
- In Docker: use a well-maintained base image that includes ffmpeg (e.g., `linuxserver/ffmpeg` or `jrottenberg/ffmpeg`), or install from a PPA that provides recent builds.
- Pin ffmpeg version and test post-processing in CI.
- Use yt-dlp's custom ffmpeg builds if available (`yt-dlp/FFmpeg-Builds`) which include patches for known compatibility issues.
- At startup, verify ffmpeg works: run `ffprobe -version` and check the return code.

**Detection:**
- Add a startup health check that downloads a known 10-second video and verifies it plays correctly
- Monitor for "Postprocessing failed" in yt-dlp output
- Check for files that are missing expected audio tracks

**Which phase should address it:** Phase 1 (Foundation) — Dockerfile/install script must include ffmpeg from day 1.

---

### Pitfall 7: No File Cleanup Policy (Disk Fills Up, Server Dies)

**What goes wrong:** Every downloaded file stays on disk indefinitely. After a few dozen downloads (or a single 8K video), the server runs out of disk space. The app crashes, health checks fail, and the container is killed.

**Why it happens:** The developer focuses on the download flow and never implements cleanup. "I'll add it later" — later never comes. Even with small files, organic usage fills disk over weeks.

**Consequences:**
- App becomes unresponsive (can't write temp files)
- Docker container killed for exceeding disk quota
- Data loss if cleanup happens without user warning
- Cloud costs from EBS/git-LFS storage bloat

**Prevention:**
- **Auto-cleanup from day 1.** Set a TTL on downloaded files (30 minutes is a common default — enough time for the user to download but not so long that disk fills).
- Implement a periodic cleanup job (cron or background thread) that deletes files older than the TTL.
- Store downloads in a temp directory (e.g., `/tmp/downloads/`) that is cleaned on container restart.
- Add a `POST /api/cleanup` endpoint for manual triggering.
- Monitor disk usage and alert at 70%, 85%, 95% thresholds.

**Detection:**
- Track total download directory size in logs
- Alert on disk usage growth rate
- Count stale files (older than TTL but not yet cleaned)

**Which phase should address it:** Phase 1 (Foundation) — cleanup must exist before any real usage. It's a simple cron job but impossible to retrofit well.

---

### Pitfall 8: Progress Reporting in Non-TTY Subprocess (Silent Downloads)

**What goes wrong:** The app spawns yt-dlp as a subprocess to show download progress to the user, but progress output is buffered or suppressed because the subprocess is not connected to a TTY. The user sees "Starting download..." followed by a long wait, then "Download complete!" — no progress bar, no ETA, no indication of life.

**Why it happens:** yt-dlp only emits real-time progress lines when running in a TTY. In non-TTY mode (subprocess.PIPE), output is buffered. The `--progress-template` option doesn't reliably force unbuffered output in subprocess mode. This is a known yt-dlp issue (#13649).

**Consequences:**
- Users think the app is frozen or broken
- Support requests: "Why isn't anything happening?"
- Users abandon the download and try another service
- Large downloads feel much longer without progress feedback

**Prevention:**
- **Use yt-dlp's Python API** (`yt_dlp.YoutubeDL`) with a `progress_hooks` callback instead of subprocess. This gives reliable per-fragment progress updates.
- If using subprocess (non-Python backends): pass `--newline` flag and use `--progress-template` with JSON output to stdout, then parse the JSON lines. The `--newline` option forces newline-delimited progress output.
- Use WebSockets (Socket.IO) to push progress updates to the frontend in real time.
- As a fallback, send periodic "still downloading" pings at 30-second intervals.

**Detection:**
- Measure time between download start and first progress event
- Log progress update frequency
- Alert if no progress update within 60 seconds of download start

**Which phase should address it:** Phase 2 (Core Backend). Progress hooks require using the Python API properly, which is an architectural choice made in Phase 1.

---

## Moderate Pitfalls

### Pitfall 9: Ignoring yt-dlp's `--impersonate` and Cookie Requirements

**What goes wrong:** The app runs yt-dlp with default settings and no cookies. YouTube returns "Sign in to confirm you're not a bot" for all requests, even from residential IPs. Downloads fail 100% of the time.

**Why it happens:** Since 2025, YouTube has progressively tightened bot detection. Default yt-dlp requests are flagged. The developer assumes yt-dlp works "out of the box" as it did in 2023.

**Prevention:**
- Include `--impersonate chrome` in all yt-dlp invocations (requires `curl_cffi` Python package)
- Provide a mechanism for users to supply cookies (e.g., upload Netscape-format cookies.txt or use `--cookies-from-browser`)
- In a web app context: the server needs its own cookie file. Ship with a guide on how to export cookies from a logged-in YouTube session.
- Install `yt-dlp-ejs` (JavaScript runtime for YouTube's JS challenges). Deno is recommended.
- Consider a PO Token provider: `YT_DLP_POT_PROVIDER_URL` environment variable.

**Which phase should address it:** Phase 2 (Core Backend) — cookie management and impersonation settings.

---

### Pitfall 10: Running Downloads on the Request Thread (Holding HTTP Connections for Minutes)

**What goes wrong:** The web server's request handler starts a yt-dlp download synchronously. The HTTP connection stays open for 1–10+ minutes while the download completes. The server runs out of worker threads/processes, and health checks start failing.

**Why it happens:** Flask's development server is single-threaded. Gunicorn has a limited worker pool. The developer treats a download like any other request handler.

**Consequences:**
- Server stops responding to new requests after 4–5 concurrent downloads
- Health check timeouts cause orchestrator to kill the container
- All users experience outages, not just the ones downloading

**Prevention:**
- Use a background task queue (Celery, RQ, or simple asyncio) for downloads.
- Or: use an async framework (FastAPI, aiohttp) that can handle long-lived connections without blocking the event loop.
- Or: use a streaming response that yields chunks as they download (Flask `Response` with generator, Node.js `pipe()`).
- Set a hard timeout on download operations (e.g., 30 minutes max, then abort and clean up).

**Which phase should address it:** Phase 2 (Core Backend). The request/worker architecture must support long-running operations.

---

### Pitfall 11: Trusting Video Metadata from yt-dlp Without Sanitization

**What goes wrong:** Video titles, descriptions, and filenames from YouTube can contain path traversal sequences (`../`), null bytes, shell metacharacters, or Unicode control characters. If used unsanitized in file paths or shell commands, they cause crashes, directory escapes, or injection vulnerabilities.

**Why it happens:** The developer assumes YouTube video titles are safe strings. In practice, titles can contain anything: `/`, `\0`, `..`, `; rm -rf /`, emoji with unexpected Unicode normalization, BiDi override characters.

**Prevention:**
- Always sanitize filenames: use `yt-dlp`'s `--restrict-filenames` option or `yt_dlp.utils.sanitize_filename()` which removes/replaces unsafe characters.
- Never use video title in paths: use a UUID-based filename and store metadata separately.
- If displaying titles in HTML, properly escape them (XSS prevention).
- Be aware of CVE-2026-50023: insufficient filename sanitization leading to arbitrary file writes.

**Which phase should address it:** Phase 1 (Foundation) — output template configuration and filename handling.

---

### Pitfall 12: No oEmbed Metadata Caching (Wasting yt-dlp Calls on Every Request)

**What goes wrong:** Every page load or URL paste triggers a yt-dlp extraction call (HTTP requests to YouTube, JS interpretation, format negotiation). Each call takes 2–5 seconds and consumes YouTube API quota / IP reputation. The same video's metadata is fetched 20+ times.

**Why it happens:** The developer uses yt-dlp for everything — both metadata (title, thumbnail) and download. yt-dlp is not optimized for metadata-only lookups; it still does heavy extraction work.

**Prevention:**
- Use the YouTube oEmbed API for initial metadata: `https://www.youtube.com/oembed?url=VIDEO_URL&format=json`. It returns title, author, thumbnail, and duration. It is **never rate-limited** and has **no IP reputation penalty**.
- Cache the oEmbed result in memory or Redis with a 10–60 minute TTL.
- Only invoke yt-dlp when the user actually initiates a download.
- For download format options, use yt-dlp's `-J` (JSON) option to dump available formats once, then cache that.

**Which phase should address it:** Phase 2 (Core Backend). oEmbed integration is a small addition but must be designed alongside the metadata flow.

---

### Pitfall 13: Assuming YouTube URLs Are the Only Input

**What goes wrong:** yt-dlp supports 1000+ sites. A user pastes a URL from a malicious site that triggers a yt-dlp exploit (HTTP redirect to a crafted URL, or a site extractor with a known vulnerability). The app becomes an open proxy for downloading from any site.

**Why it happens:** The developer passes `yt-dlp {url}` without restricting which extractors can be used. The "generic extractor" in yt-dlp matches *all* URLs.

**Prevention:**
- Explicitly restrict yt-dlp to YouTube only: `--ies youtube` (ignore extractors: `default,-generic`).
- Validate the URL domain before passing to yt-dlp: check it matches `youtube.com`, `youtu.be`, `m.youtube.com`, `www.youtube.com`.
- Set `--default-search "ytsearch"` to prevent accidental web searches.
- This also prevents abuse of your service as a generic download proxy.

**Which phase should address it:** Phase 1 (Foundation) — extractor restriction is a yt-dlp configuration option set at the start.

---

### Pitfall 14: No Graceful Handling of DRM-Protected or Private Videos

**What goes wrong:** YouTube videos with DRM (Widevine), paid content (rentals/purchases), or private/unlisted-with-restrictions fail with confusing errors. The app shows a generic "Download failed" message with no actionable information.

**Why it happens:** yt-dlp cannot bypass Widevine DRM. It also cannot download videos that require payment. The error from yt-dlp is technical ("UNPLAYABLE", "ERROR: This video requires payment"), and the app doesn't translate it.

**Prevention:**
- Catch specific yt-dlp error types and map them to user-friendly messages:
  - "This video is protected by DRM and cannot be downloaded"
  - "This video requires payment to watch"
  - "This video is private or unavailable"
- Make the playability_status from YouTube's response visible in logs for debugging.
- Don't retry these — they're permanent failures.

**Which phase should address it:** Phase 2 (Core Backend) — error handling refinement.

---

## Minor Pitfalls

### Pitfall 15: Choosing the Wrong Quality Format String

**What goes wrong:** Using `bestvideo+bestaudio` without height constraints selects 4K/8K video, resulting in huge files (2–8 GB) and slow downloads. Using `best` alone selects a progressive format which may be limited to 720p on YouTube.

**Why it happens:** Format selection in yt-dlp is powerful but confusing. The defaults are optimized for archive-quality, not for a web app.

**Prevention:**
- Let the user choose quality from a curated list (360p, 480p, 720p, 1080p) rather than exposing raw yt-dlp format strings.
- Use format strings like: `bestvideo[height<=1080]+bestaudio/best[height<=1080]` for sensible defaults.
- Fall back to `bestvideo+bestaudio/best` if the constrained format isn't available.

**Which phase should address it:** Phase 2 (Core Backend) — format selection UI.

### Pitfall 16: Not Handling Non-YouTube Sites Warning Label

When YouTube changes things, yt-dlp releases notes will call this out. Missing this in logs means confusion.

### Pitfall 17: Development vs Production Divergence

**What goes wrong:** The app works perfectly on the developer's laptop (residential IP, macOS with ffmpeg pre-installed, GUI browser with logged-in YouTube cookies) but fails completely in production (datacenter IP, Docker without ffmpeg, no cookies).

**Why it happens:** The developer tests only in their local environment, which differs from production in three critical ways: IP reputation, ffmpeg availability, and cookie state.

**Prevention:**
- Test in a staging environment that mirrors production infrastructure (same cloud provider, same Docker image).
- Add startup health checks that verify: yt-dlp works, ffmpeg works, YouTube extraction works.
- Use Docker locally with the same image as production.
- Test with `cookies`: none initially — if it works without cookies locally but not in production, you've identified the IP-blocking problem early.

**Which phase should address it:** Phase 1 (Foundation) — CI/staging setup.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Phase 1: Foundation** (Docker, CI, scaffolding) | No ffmpeg in Docker image; stale yt-dlp version; no streaming architecture | Pin ffmpeg, use yt-dlp nightly, design streaming from the start |
| **Phase 2: Core Backend** (download API, format selection, progress) | Subprocess injection; buffer-in-memory; no rate-limiting queue; no progress feedback | Use Python API with `progress_hooks`; stream to disk then to client; serialize YouTube requests |
| **Phase 3: Frontend** (UI, download button, progress bar) | Infinite spinner because backend doesn't report progress; broken downloads with no error message | Design frontend around backend's actual event model (see Pitfall 8) |
| **Phase 4: Polish** (error handling, edge cases, docs) | Generic error messages don't distinguish "private video" from "rate limited" from "yt-dlp outdated" | Map yt-dlp exit codes and error patterns to specific user-facing messages |
| **Production hardening** | Datacenter IP blocks cause 100% failure rate in production | Test in production-like environment before launch (see Pitfall 17) |

---

## Post-Mortem / Real-World Failure Patterns

From production YouTube downloader services (VidPickr, CRtheHILLS/yt-dlp-rescue, community reports):

1. **"Works on my machine" -> production failure** is the #1 reported pattern. Local dev environments have residential IPs, production servers have datacenter IPs. YouTube blocks datacenter IPs at the network layer. This cannot be fixed with cookies alone.

2. **Player JS rotation breaks everything overnight.** Multiple services report waking up to 100% failure rates after a YouTube player update. The fix is always to update yt-dlp to the latest nightly. Auto-update is not optional.

3. **Rate limiting from parallel requests** kills service for all users. A single user spamming the download button can ban the server's IP for an hour. Queue serialization is mandatory.

4. **oEmbed API as a first-line metadata fetch** is a universally recommended pattern. It's free, unlimited, never blocked, and eliminates 90% of yt-dlp calls (which now only happen for actual downloads).

5. **Residential proxy requirement for high-throughput.** Multiple production services confirm: the only reliable way to download from YouTube on cloud infrastructure is through residential proxies. For a simple single-user app, running on a home server or browser-side download is the pragmatic alternative.

---

## Sources

- yt-dlp official troubleshooting & FAQ: https://yt-dlp-yt-dlp.mintlify.app/reference/troubleshooting
- yt-dlp changelog (CVE history): https://github.com/yt-dlp/yt-dlp/blob/HEAD/Changelog.md
- yt-dlp embed API docs: https://yt-dlp-yt-dlp.mintlify.app/advanced/embedding
- yt-dlp issue #14404 (new JS requirements): https://github.com/yt-dlp/yt-dlp/issues/14404
- yt-dlp issue #15770 (HTTP 429 on VPS): https://github.com/yt-dlp/yt-dlp/issues/15770
- yt-dlp issue #16379 (pip nightly update failures): https://github.com/yt-dlp/yt-dlp/issues/16379
- CRtheHILLS/yt-dlp-rescue (production anti-bot guide): https://github.com/CRtheHILLS/yt-dlp-rescue
- VidPickr failure analysis: https://vidpickr.com/blog/why-youtube-downloads-fail-2026-data
- VidPickr anti-bot evolution: https://vidpickr.com/blog/youtube-anti-bot-evolution-2026
- DEV post on IP trafficking: https://dev.to/osovsky/i-was-building-a-cloud-video-service-youtube-turned-me-into-an-ip-trafficker-1l9o
- Reddit r/youtubedl common mistakes: https://www.reddit.com/r/youtubedl/comments/1nevry1/common_mistakes_when_using_ytdlp/
- CVE-2026-26331 (netrc-cmd injection): https://nvd.nist.gov/vuln/detail/CVE-2026-26331
- CVE-2026-50574 (aria2c injection): https://nvd.nist.gov/vuln/detail/CVE-2026-50574
- CVE-2026-50019 (cookie leak): https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-f7j3-774f-rfhj
- CVE-2026-50023 (filename sanitization): https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-c6mh-fpjc-4pr3
- Python subprocess PIPE deadlock warning: https://docs.python.org/3/library/subprocess.html
- yt-dlp issue #13649 (progress buffering in non-TTY): https://github.com/yt-dlp/yt-dlp/issues/13649
- yt-dlp issue #4338 (downloading to buffer): https://github.com/yt-dlp/yt-dlp/issues/4338
