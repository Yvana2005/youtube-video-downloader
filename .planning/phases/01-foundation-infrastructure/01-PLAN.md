# Phase 1: Foundation & Infrastructure - Plan

**Planned:** 2026-07-06
**Goal:** Flask server boots, yt-dlp auto-update, temp file management, streaming architecture, security guardrails

**Wave 1:** Bootstrap — create app.py skeleton with Flask server, yt-dlp integration, streaming architecture

**Requirements addressed:** INFRA-01, INFRA-02, INFRA-03, ERR-04

---

## Architecture Overview

Single-file Flask application with:
- yt-dlp Python API integration with auto-update
- Streaming file response (no memory buffering)
- Temp file management with cleanup daemon
- Security validation (URL patterns, extractor restriction)

---

## Wave 1: Bootstrap

### Plan 01-01: Create Flask app skeleton

<objective>Create the foundational Flask application structure</objective>

<tasks>
<task>
<action>Create app.py with Flask server, yt-dlp integration, and streaming architecture</action>
<read_first>
- .planning/phases/01-foundation-infrastructure/01-RESEARCH.md
- .planning/phases/01-foundation-infrastructure/01-CONTEXT.md
</read_first>
<acceptance_criteria>
- [ ] app.py exists at project root
- [ ] Flask server starts with `python app.py`
- [ ] Server responds on localhost:5000
- [ ] yt-dlp auto-update on startup
- [ ] Temp file cleanup daemon running
- [ ] URL validation implemented
- [ ] Streaming response pattern used
</acceptance_criteria>
<verify>python app.py & sleep 2 && curl -s localhost:5000/ 2>/dev/null && kill $!</verify>
</task>

<task>
<action>Implement yt-dlp auto-update on startup</action>
<read_first>
- 01-01 task (above)
</read_first>
<acceptance_criteria>
- [ ] yt-dlp.update.update_self() called on app startup
- [ ] Startup logs show update check
- [ ] Nightly channel configured
</acceptance_criteria>
<verify>grep -q "update_self()" app.py && echo "update_self present"</verify>
</task>

<task>
<action>Implement temp file management with cleanup daemon</action>
<read_first>
- 01-01 task (above)
</read_first>
<acceptance_criteria>
- [ ] tempfile.mkdtemp() used for per-request directories
- [ ] Cleanup thread deletes files older than 10 minutes
- [ ] Daemon runs every 5 minutes
</acceptance_criteria>
<verify>python -c "import tempfile; print('mkdtemp available')" && python -c "import threading; print('threading available')"</verify>
</task>

<task>
<action>Implement URL validation (D-08) and security guardrails (D-09, D-10)</action>
<read_first>
- 01-01 task (above)
</read_first>
<acceptance_criteria>
- [ ] Validate URLs match `youtube.com/watch?v=` or `youtu.be/` pattern before passing to yt-dlp
- [ ] Hardcode `outtmpl` template to prevent path traversal
- [ ] Restrict yt-dlp extractors to `[youtube]` only
- [ ] Use Python API with list-form arguments (not string interpolation)
</acceptance_criteria>
<verify>grep -E "youtube\.com/watch\?v=|youtu\.be/" app.py && grep -F "outtmpl=" app.py && grep -E "extractors.*\[youtube\]|'youtube'|\"youtube\"" app.py && grep -v 'YoutubeDL\("' app.py || echo "No string interpolation in constructor"</verify>
</task>

<task>
<action>Implement Deno runtime verification (D-12)</action>
<read_first>
- 01-01 task (above)
</read_first>
<acceptance_criteria>
- [ ] Verify Deno >= 2.0.0 on startup with clear error if missing
- [ ] Check node -v or deno --version availability
</acceptance_criteria>
<verify>python -c "import subprocess; result = subprocess.run(['deno', '--version'], capture_output=True, text=True); print('deno >= 2.0.0' if result.returncode == 0 and result.stdout.split()[1].startswith('2.') else 'deno missing or < 2.0.0')"</verify>
</task>

<task>
<action>Implement global Flask error handlers (D-13)</action>
<read_first>
- 01-01 task (above)
</read_first>
<acceptance_criteria>
- [ ] Register global Flask error handlers for 400/404/500
- [ ] Error handlers return structured JSON responses
</acceptance_criteria>
<verify>grep -r "@app.errorhandler" app.py || echo "errorhandler not found"</verify>
</task>

<task>
<action>Implement yt-dlp exception mapping (D-14)</action>
<read_first>
- 01-01 task (above)
</read_first>
<acceptance_criteria>
- [ ] Map DownloadError, ExtractorError, and other yt-dlp exceptions to user-friendly messages
- [ ] Global exception handler catches yt-dlp-specific errors
</acceptance_criteria>
<verify>grep -r "DownloadError\|ExtractorError" app.py && echo "yt-dlp exceptions mapped" || echo "need error handling"</verify>
</task>
</tasks>

<must_haves>
<truths>
- Flask server must start and respond on localhost:5000
- yt-dlp must auto-update to nightly on startup
- Temp files must be cleaned up after 10 minutes
- Large files must be streamed in chunks, not buffered
- ffmpeg must be detected on startup
- Missing ffmpeg must be logged as warning
- Only youtube.com/youtu.be URLs accepted (D-08)
- outtmpl must be hardcoded to prevent path traversal (D-09)
- Extractors restricted to [youtube] only (D-10)
- Deno >= 2.0.0 verified on startup (D-12)
- Global error handlers for 400/404/500 registered (D-13)
- yt-dlp exceptions mapped to user-friendly messages (D-14)
</truths>
<artifacts>
- path: app.py
  provides: Flask application with yt-dlp integration, streaming, security guardrails
  min_lines: 150
</artifacts>
</must_haves>

<files_modified>
- app.py (create)
</files_modified>

<autonomous>true</autonomous>

</plan>

---

## Success Criteria

1. Running `python app.py` starts the Flask dev server that responds on localhost
2. yt-dlp auto-updates to the latest nightly build on application startup (verified in startup logs)
3. Temporary download files are created in isolated per-request directories under /tmp and automatically cleaned up after 10 minutes
4. Large files are streamed in chunks (not buffered entirely in memory), verified by downloading a large test file
5. Missing ffmpeg is detected on startup and logged as a warning

---

## Verification

- [ ] Flask server starts successfully
- [ ] yt-dlp update check runs at startup
- [ ] Temp directory creation works
- [ ] Cleanup daemon is running
- [ ] Streaming response works for large files