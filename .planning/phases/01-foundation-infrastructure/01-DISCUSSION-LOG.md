# Phase 1: Foundation & Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2025-07-06
**Phase:** 1-Foundation & Infrastructure
**Areas discussed:** Project structure, yt-dlp integration, streaming architecture, temp file management, security, JS runtime, error handling

**Mode:** auto (all decisions auto-selected with recommended defaults)

---

## Project Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single app.py | Minimal structure, one file | ✓ |
| Flask blueprints | Modular, organized by concern | |
| Multi-file package | src/ layout with separation | |

**User's choice:** Single app.py (simplest possible)
**Notes:** Auto-selected. Phase 1 is small enough for one file. Can refactor later if needed.

---

## yt-dlp Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Python API (YoutubeDL class) | Safe, no subprocess risks | ✓ |
| Subprocess call | Separate process, JSON parsing | |

**User's choice:** Python API (secure default)
**Notes:** Auto-selected. Python API is safer and gives direct access to progress hooks.

---

## Streaming Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Temp file + send_file | yt-dlp writes to disk, Flask sends | ✓ |
| In-memory streaming | BytesIO in memory | |

**User's choice:** Temp file + send_file
**Notes:** Auto-selected. yt-dlp writes to disk natively — streaming from there is the standard pattern.

---

## Temp File Management

| Option | Description | Selected |
|--------|-------------|----------|
| Per-request temp dir + cleanup daemon | Each request gets isolated dir, daemon sweeps old files | ✓ |
| Shared temp dir + single cleanup | One directory, simpler cleanup logic | |

**User's choice:** Per-request temp dir + cleanup daemon
**Notes:** Auto-selected. Isolated dirs prevent request collisions, daemon handles abandoned downloads.

---

## Security

| Option | Description | Selected |
|--------|-------------|----------|
| URL validation + hardcoded outtmpl + restricted extractors | Defense in depth | ✓ |
| Basic URL check only | Minimal validation | |

**User's choice:** Defense in depth (recommended)
**Notes:** Auto-selected. URL validation, hardcoded output path, extractor restrictions all non-negotiable per research pitfall analysis.

---

## JS Runtime

| Option | Description | Selected |
|--------|-------------|----------|
| Deno >= 2.0.0 | Recommended by yt-dlp, sandboxed | ✓ |
| Node.js >= 22 | Fallback option | |

**User's choice:** Deno >= 2.0.0 (yt-dlp recommended)
**Notes:** Auto-selected. Deno is sandboxed and preferred by the yt-dlp project. Verify on startup.

---

## Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Global handlers + exception mapping | Centralized + specific per error type | ✓ |
| Per-route try/except | Simpler but repetitive | |

**User's choice:** Global handlers + exception mapping
**Notes:** Auto-selected. Flask error handlers for HTTP, yt-dlp exception mapping for download-specific errors.

---

## the agent's Discretion

- HTTP server: Flask dev server (single-user local tool, no production deployment planned)
- Startup: `python app.py` with `app.run(debug=True)`

## Deferred Ideas

None — discussion stayed within phase scope
