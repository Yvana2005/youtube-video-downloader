# YouTube Video Downloader

## What This Is

A simple web application that lets users download YouTube videos by pasting a URL. Minimal UI, single purpose — paste a link, get the file.

## Core Value

User can paste a YouTube link and download the video file in their chosen format.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can paste a YouTube URL and see available download options
- [ ] User can select video format and quality
- [ ] User can download the selected video file
- [ ] Application handles errors gracefully (invalid URLs, unavailable videos)

### Out of Scope

- Batch/multiple URL downloads — single video at a time
- User accounts or authentication — no login system
- Playlist downloading — single video only
- Audio extraction (MP3) — v2 consideration

## Context

Greenfield project. Built as simple as possible — single-page web app with a backend that wraps yt-dlp.

## Constraints

- **Simplicity**: Must be the simplest possible solution — minimal dependencies, minimal code
- **Single user**: No multi-user concerns

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| — | To be decided during research/planning | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2025-07-06 after initialization*
