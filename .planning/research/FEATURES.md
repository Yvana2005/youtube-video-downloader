# Feature Landscape: YouTube Video Downloader Web App

**Domain:** Single-purpose YouTube video downloader web app
**Researched:** 2026-07-06
**Mode:** Ecosystem research (Features dimension)
**Overall confidence:** HIGH

> **Project constraint reminder:** Per PROJECT.md — single video at a time, no user accounts, no playlist support, no MP3 extraction in v1 (v2 consideration). This is a minimal single-purpose web app, not a media platform.

---

## Table Stakes

Features users expect from *any* YouTube downloader web app. Missing any of these → product feels broken or incomplete.

| # | Feature | Why Expected | Complexity | Notes |
|---|---------|--------------|------------|-------|
| 1 | **Paste URL → see download options** | Every web downloader (Y2Mate, YT1s, SaveFrom, etc.) works this way. This is the core interaction model users know. | Low | Single input field, paste-and-go. Must show video info (title, thumbnail) before download. |
| 2 | **MP4 format download** | MP4 is the universal video format. Users expect it by default. Every competitor offers it. | Low | yt-dlp provides MP4 natively. No conversion needed for most quality tiers. |
| 3 | **Quality/resolution selection** | Users expect a choice — 360p (fast/small), 720p (good balance), 1080p (HD). Competitors all offer tiered quality. | Low | yt-dlp's `-f` flag provides resolution options. Caveat: YouTube serves 1080p+ as separate video + audio streams, requiring merge via ffmpeg. |
| 4 | **Error handling: invalid URL** | Users paste wrong links. App must not crash — show "Invalid YouTube URL" message. | Low | Simple regex validation on the URL + yt-dlp error code mapping. |
| 5 | **Error handling: unavailable video** | Private/deleted/age-restricted videos. Must tell user why download failed. | Low-Medium | yt-dlp returns specific exit codes for "video unavailable", "age restricted", etc. Map to user-facing messages. |
| 6 | **Mobile-friendly UI** | Most users access these tools from phones. Y2Mate, YT1s all work on mobile. | Low | Responsive design, touch-friendly input. No desktop-only layouts. |
| 7 | **No registration required** | Every web downloader is anonymous. Registration would be instant rejection. | Low | Simply don't build auth. State stored server-side or not at all. |
| 8 | **Free to use** | Every competitor is free (some have PRO tiers, but basic download is free). | Low | Cost is bandwidth + storage on your server. No third-party API costs (yt-dlp is free). |
| 9 | **Works immediately (no install)** | Web vs desktop expectation is zero setup. Paste link → get file. | Low | This is inherent to the web app model. |
| 10 | **Fast response after paste** | Competitors show video info (title, thumbnail, duration, available qualities) within 2-3 seconds after URL submission. | Medium | Requires yt-dlp metadata extraction call (`--dump-json` or `-j` flag). Slower for long videos. Must cache or stream results. |

### Table Stakes — Edge Cases

| Edge Case | Expected Behavior | Complexity |
|-----------|-------------------|------------|
| YouTube Shorts URL | Must be treated as a valid video URL | Low |
| YouTube Music URL | Must be recognized as valid (even if MP3 extraction is v2) | Low |
| Long videos (>2 hours) | Must handle without timeout on extraction or download | Medium |
| Non-YouTube URL pasted | Clear validation error, not a crash or generic failure | Low |
| Network disconnection mid-download | Resume not expected (no session state), but app must not hard-fail | Low |
| Cookie/age-restricted content | Should show "Age restricted — cannot download" rather than hang | Medium |

---

## Differentiators

Features that would set this app apart from the competition. Most web-based downloaders in this space are ad-infested, slow, or limit quality for free users. These differentiators play to the strengths of a clean, self-hosted app.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| D1 | **No ads, no popups, no redirects** | This is the single biggest UX win. Every competitor (Y2Mate, YT1s, SaveFrom, Y2meta) is overrun with ads, pop-ups, and malicious redirects. A clean, ad-free experience is a massive differentiator. | Low | Self-hosted eliminates the monetization pressure that drives ad-infested UIs. This is the app's primary competitive advantage. |
| D2 | **Real-time download progress** | Most web tools show a spinner and then serve the file. Showing actual percentage/speed/ETA feels premium. | Medium | Uses yt-dlp's progress hooks or WebSocket streaming to frontend. Adds ~1-2 days dev time. |
| D3 | **Video preview (thumbnail + metadata)** | Showing video title, channel name, duration, and thumbnail *before* download confirms the user has the right video. Most web tools do this, but doing it cleanly (no ads around it) is the differentiator. | Low | yt-dlp `--dump-json` returns title, thumbnail URL, duration, channel, etc. |
| D4 | **File size indicator** | Users want to know "how big is this file?" before committing to a download. Few web tools show this. | Low-Medium | yt-dlp's JSON output includes `filesize` or `filesize_approx`. |
| D5 | **Dark mode** | Many developer/tech users run dark mode OS-wide. A toggle or auto-detection shows polish. | Low | CSS custom properties + `prefers-color-scheme` media query. No framework needed. |
| D6 | **Download queue (simple)** | User can paste multiple URLs while one is processing. Downloads run sequentially. | Medium | Queue state in memory (no persistence since no accounts). Sequential to keep resource usage predictable. |
| D7 | **URL validation + auto-fetch** | System automatically fetches video info after paste (no "Convert" button click needed). Reduces friction. | Medium | Debounced URL input that triggers yt-dlp metadata fetch. Must handle rapid typing gracefully. |

### Differentiator Priority

For MVP, focus on **D1** (no ads — inherent to the app design itself) and **D3** (video preview). These deliver the most value for the least effort.

---

## Anti-Features

Features to explicitly NOT build. These conflict with the project's simplicity constraint or introduce complexity without commensurate value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|--------------------|
| **User accounts / authentication** | PROJECT.md explicitly excludes this. Adds auth state, session management, password storage, security surface. Zero value for a single-user download tool. | Run as a completely anonymous service. |
| **Playlist/channel downloads** | PROJECT.md out of scope. Adds significant complexity: playlist parsing, multiple sequential downloads, output organization, progress tracking. | Single video only. If playlist URL is pasted, show an error. |
| **Batch/multiple URL upload** | PROJECT.md out of scope. File upload, queue management, completion notification — substantial UI + backend work. | Single paste field. One URL at a time. |
| **Built-in video player** | Users don't need a player — they want the file. Adds UI surface area, streaming complexity, codec concerns. | Serve the file. User plays locally. |
| **Format conversion (e.g. MP4 → AVI)** | yt-dlp downloads native formats. Re-encoding is CPU-intensive and rarely needed. Most users want MP4. | Only offer formats yt-dlp provides natively. |
| **Cloud storage integration (Google Drive, Dropbox)** | Drastically expands scope. OAuth flows, API rate limits, storage quotas. | Files are downloaded directly to user's device. |
| **Crypto/mining monetization** | Destroys trust, is detectable by ad blockers, and violates project ethics. | No monetization — self-hosted tool. |
| **Download history / recently downloaded** | Implies state persistence and potentially storage management UI. | Stateless. Completed state is transient. |
| **Browser extension** | Requires separate development, cross-browser testing, Chrome Web Store/AMO publishing, maintenance. Users can bookmark or type the URL. | Provide a bookmarklet as an optional convenience. |
| **Rate limiting / daily download caps** | Common in commercial tools to upsell PRO. Feels hostile. | No limits — your server, your bandwidth. |
| **Captcha / anti-bot** | Competitors use this to reduce server load. Creates friction. | If server load is a concern, use a simple queue rather than captcha. |

---

## Feature Dependencies

```
youtube URL
  └── URL validation (must be valid YouTube URL)
       └── Metadata fetch (title, thumbnail, available formats)
            ├── Format display (show user options)
            └── Quality filter (deduplicate resolutions)
                 └── Download trigger
                      ├── Progress tracking
                      └── File delivery
```

### Dependency Map

```
Feature                            Depends On                          Blocks
────────────────────────────────── ─────────────────────────────────── ──────────────────────────
URL validation                     —                                  Metadata fetch
Metadata fetch                     URL validation                      Format display, quality filter
Format display                     Metadata fetch                      Download trigger
Quality filter                     Metadata fetch                      Download trigger
File size indicator                Metadata fetch                      —
Download progress                  Download trigger                    —
Dark mode                          —                                   —
Mobile-friendly UI                 —                                   —
Error handling (invalid URL)       URL validation                      —
Error handling (unavailable)       Metadata fetch / Download trigger   —
Download queue                     Download trigger                     —
```

---

## MVP Recommendation

This app's competitive advantage is simplicity itself — clean, fast, ad-free. The MVP should ship the absolute minimum while feeling complete and polished.

### Must Have (MVP)

1. **Paste URL → auto-fetch metadata** — Single input, debounced fetch. Show title, thumbnail, duration, available qualities.
2. **Quality selection** — Radio buttons or dropdown. Common tiers: 360p, 480p, 720p, 1080p. Show file size if available.
3. **Download execution** — Button triggers yt-dlp. Show progress during processing.
4. **File delivery** — Stream the completed file to the user's browser via download prompt.
5. **Error handling** — Invalid URL, unavailable video, network errors all have clear messages.
6. **Mobile-responsive UI** — Works on phone screens.
7. **Clean, ad-free interface** — This is the differentiator. A beautiful blank page with a centered input.

### Should Have (Post-MVP, high value)

8. **Dark mode** — Low effort, high polish signal.
9. **Download queue** — Especially useful since processing takes time. Let user stack URLs.
10. **Progress bar with ETA** — Changes feel from "did it break?" to "this is professional."

### Won't Have (v1)

11. **MP3 extraction** — Per PROJECT.md, v2 consideration. Ubiquitous expectation but intentionally deferred.
12. **Subtitle download** — Niche. Add if requested.
13. **Format conversion** — MP4 only. No AVI, MKV, etc.
14. **Custom filename / output path** — Over-engineering for a single-user tool.
15. **Bookmarklet** — Nice-to-have, defer.

### MVP Feature Comparison vs Competitors

| Feature | This App (MVP) | Y2Mate / YT1s | SaveFrom | MeTube (self-hosted) |
|---------|---------------|---------------|----------|---------------------|
| Ad-free | ✅ **Yes** | ❌ Popup hell | ❌ Some ads | ✅ Yes |
| Paste URL → download | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Quality selection | ✅ Yes | ✅ Yes | ⚠️ 360p free | ✅ Yes |
| Video preview | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| File size shown | ⚠️ If available | ❌ No | ❌ No | ❌ No |
| Progress indicator | ✅ Yes | ⚠️ Spinner only | ⚠️ Spinner only | ✅ Yes |
| Mobile-friendly | ✅ Yes | ✅ Yes | ⚠️ Average | ⚠️ Basic |
| Download queue | ⚠️ Sequential | ❌ No | ❌ No | ✅ Yes (configurable) |
| Dark mode | ⚠️ Post-MVP | ❌ No | ❌ No | ✅ Yes |
| Playlist support | ❌ No | ✅ Yes | ❌ No | ✅ Yes |
| MP3 extraction | ❌ v2 | ✅ Yes | ✅ Yes | ✅ Yes |
| Login required | ❌ No | ❌ No | ❌ No | ⚠️ Optional |
| Multi-site support | ❌ YouTube only | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Market Context

The YouTube downloader web app space in 2026 is dominated by ad-supported sites (Y2Mate, YT1s, SaveFrom) that deliver the core function but deliver a terrible UX through aggressive advertising. Many free web tools cap quality at 720p or 360p to push desktop app installs.

The self-hosted alternatives (MeTube, yt-dlp-web-ui, TubeArchivist) target power users who run Docker at home. They're more powerful but also more complex to set up.

**Opportunity:** A *deployed* (not self-hosted) web app that is as simple as Y2Mate but as clean as MeTube, with no ads, no limits, and no upsells. This fills the gap between "ad-infested free tools" and "complex self-hosted Docker containers."

**Risk of this being a differentiator:** Low, because the differentiator is simply *not doing what competitors do* (ads, popups, quality caps). That's sustainable only if hosting costs (bandwidth for serving video files) remain manageable.

---

## Sources

- **Competitor analysis:** Y2Mate, YT1s, SaveFrom, Y2meta, VidsSave, 4K Video Downloader Plus (web versions)
- **Self-hosted open-source projects:** MeTube (14k ⭐), yt-dlp-web-ui (2.5k ⭐), yt-webui
- **Industry comparisons:** ScreenApp (tested June 2026), SoftwareTestingHelp (tested June 2026), TechyFlavors (April 2026), TechBloat (May 2026), Gizmochina (May 2026)
- **Backend reference:** yt-dlp documentation, feature flags, format selection API

**Confidence in findings:** HIGH — feature landscape is well-established and has not shifted significantly in the past 2+ years. Minor twists (YouTube Shorts, cookie requirements for downloads) are edge cases, not core flow changes.
