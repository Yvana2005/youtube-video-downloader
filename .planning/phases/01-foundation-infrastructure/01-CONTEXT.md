# Phase 1: Foundation & Infrastructure - Context

**Gathered:** 2025-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Flask server skeleton that boots with a single command, integrates yt-dlp with auto-update, manages temporary download files, establishes streaming architecture, and enforces security guardrails. No API routes or frontend yet — those are Phase 2 and Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** Single `app.py` file for MVP — minimal structure, no blueprints or packages until needed

### yt-dlp Integration
- **D-02:** Use Python API (`YoutubeDL` class) — safer than subprocess, avoids shell injection vectors
- **D-03:** Auto-update to nightly build on application startup via `yt_dlp.update.update_self()`

### Streaming Architecture
- **D-04:** yt-dlp downloads to a temp file, Flask streams it to the client via `send_file` with generator
- **D-05:** Files are never fully buffered in memory — streaming in chunks

### Temp File Management
- **D-06:** Per-request temp directory created with `tempfile.mkdtemp()`
- **D-07:** Daemon cleanup thread sweeps files older than 10 minutes as a safety net

### Security
- **D-08:** Validate URLs match `youtube.com/watch?v=` or `youtu.be/` pattern before passing to yt-dlp
- **D-09:** Hardcode `outtmpl` template to prevent path traversal
- **D-10:** Restrict yt-dlp extractors to `[youtube]` only
- **D-11:** Use the Python API with list-form arguments (not string interpolation)

### JS Runtime
- **D-12:** Require Deno >= 2.0.0 — verify on startup with clear error if missing

### Error Handling
- **D-13:** Global Flask error handlers for 400/404/500
- **D-14:** Specific yt-dlp exception mapping to user-friendly messages (DownloadError, ExtractorError, etc.)

### the agent's Discretion
- HTTP server choice: Flask dev server is fine for MVP (single-user local tool)
- Startup script: `python app.py` with `app.run()` is simplest; consideration of `flask run` or gunicorn deferred

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project overview, core value, requirements
- `.planning/REQUIREMENTS.md` — Full v1 requirements with IDs
- `.planning/ROADMAP.md` — Phase structure and dependencies

### Research
- `.planning/research/STACK.md` — Stack recommendations with versions
- `.planning/research/ARCHITECTURE.md` — Component boundaries and data flow
- `.planning/research/PITFALLS.md` — Known pitfalls and mitigations
- `.planning/research/SUMMARY.md` — Synthesized research findings

### Skills
- `~/.agents/skills/youtube-downloader/SKILL.md` — YouTube downloader skill (reference for yt-dlp usage)
- `~/.agents/skills/webapp-testing/SKILL.md` — Web app testing patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — greenfield project

### Established Patterns
- No existing patterns — first phase

### Integration Points
- Phase 2 builds API routes on top of this foundation
- Phase 3 adds the frontend UI

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants the simplest possible solution.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1-Foundation & Infrastructure*
*Context gathered: 2025-07-06*
