#!/usr/bin/env python3
"""YouTube Video Downloader — Flask backend with yt-dlp integration.

Single-file application (D-01).  Provides:
  • POST /info    — video metadata and available formats
  • POST /download — stream video file (added in Task 2)

SECURITY: extractors restricted to [youtube] (D-10), hardcoded outtmpl (D-09),
list-form arguments only (D-11), URL validation (D-08).
"""

from __future__ import annotations

import atexit
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import typing
import uuid
from pathlib import Path

import yt_dlp
from flask import Flask, Response, jsonify, render_template, request, send_file
from werkzeug.exceptions import HTTPException

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TEMP_TTL_SECONDS = 600            # 10 minutes before cleanup (D-07)
CLEANUP_INTERVAL_SECONDS = 300    # sweep every 5 minutes
CHUNK_SIZE = 8192                 # streaming chunk size (D-05)
DOWNLOAD_TIMEOUT = 1800           # max seconds before background download is aborted

# ---------------------------------------------------------------------------
# Download Progress State
# ---------------------------------------------------------------------------
_download_tasks: dict[str, dict] = {}
_downloads_lock = threading.Lock()


class _DownloadState:
    """Factory for initial download task state dicts."""

    @staticmethod
    def initial() -> dict:
        return {
            "status": "queued",          # queued | downloading | completed | error
            "percent": 0.0,
            "speed": None,               # bytes/sec
            "eta": None,                 # seconds
            "downloaded_bytes": 0,
            "total_bytes": None,
            "file_path": None,
            "filename": None,
            "error_message": None,
        }


def _make_progress_hook(download_id: str):
    """Return a progress_hooks closure for yt-dlp that updates _download_tasks."""
    def _hook(d: dict) -> None:
        with _downloads_lock:
            try:
                state = _download_tasks.get(download_id)
                if state is None:
                    return
                status = d.get("status", "")
                downloaded = d.get("downloaded_bytes", 0) or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                speed = d.get("speed")
                eta = d.get("eta")
                filename = d.get("filename")

                state["downloaded_bytes"] = downloaded
                state["speed"] = speed
                state["eta"] = eta

                if total:
                    state["total_bytes"] = total
                    if total > 0:
                        state["percent"] = min(downloaded / total * 100.0, 100.0)

                if filename:
                    state["filename"] = filename

                if status == "finished":
                    state["status"] = "completed"
                    state["percent"] = 100.0
                    state["eta"] = 0
            finally:
                pass  # lock released by context manager

    return _hook


def _background_download(download_id: str, url: str, format_id: str) -> None:
    """Run yt-dlp download in a background thread with progress tracking."""
    try:
        with _downloads_lock:
            if download_id in _download_tasks:
                _download_tasks[download_id]["status"] = "downloading"

        temp_dir = create_temp_dir()

        # Fetch info to validate format_id
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        available_ids = {f.get("format_id") for f in info.get("formats", [])}
        if format_id not in available_ids:
            with _downloads_lock:
                if download_id in _download_tasks:
                    _download_tasks[download_id].update(
                        status="error",
                        error_message=f"Invalid format_id: {format_id!r}. Available formats: {', '.join(sorted(available_ids, key=lambda x: (x.isdigit(), x)))}",
                    )
            return

        selected = next(
            (f for f in info.get("formats", []) if f.get("format_id") == format_id),
            {},
        )
        ext = selected.get("ext", "mp4")

        opts = _download_opts(temp_dir, format_id)
        opts["progress_hooks"] = [_make_progress_hook(download_id)]

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # Find downloaded file
        downloaded = list(temp_dir.glob("*"))
        if not downloaded:
            with _downloads_lock:
                if download_id in _download_tasks:
                    _download_tasks[download_id].update(
                        status="error",
                        error_message="Download completed but output file not found.",
                    )
            return

        download_path = str(downloaded[0])
        title = info.get("title", info.get("id", "video"))
        safe_filename = re.sub(r"[^\w\s.-]", "", f"{title}.{ext}")

        with _downloads_lock:
            if download_id in _download_tasks:
                _download_tasks[download_id].update(
                    status="completed",
                    percent=100.0,
                    file_path=download_path,
                    filename=safe_filename,
                    eta=0,
                )

    except yt_dlp.utils.DownloadError as exc:
        cause = getattr(exc, "cause", exc)
        app_error = _map_ytdlp_error(
            cause if isinstance(cause, yt_dlp.utils.ExtractorError) else exc
        )
        with _downloads_lock:
            if download_id in _download_tasks:
                _download_tasks[download_id].update(
                    status="error", error_message=app_error.message
                )
    except yt_dlp.utils.ExtractorError as exc:
        app_error = _map_ytdlp_error(exc)
        with _downloads_lock:
            if download_id in _download_tasks:
                _download_tasks[download_id].update(
                    status="error", error_message=app_error.message
                )
    except Exception as exc:
        log.exception("Unexpected error in background download %s", download_id)
        with _downloads_lock:
            if download_id in _download_tasks:
                _download_tasks[download_id].update(
                    status="error",
                    error_message="An unexpected error occurred during download. Please try again.",
                )


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ===================================================================
# yt-dlp Auto-Update (D-03)
# ===================================================================


def update_yt_dlp() -> None:
    """Auto-update yt-dlp to the latest nightly build on startup.

    This is critical for continued YouTube compatibility — YouTube rotates
    player JS every 1-3 weeks and a stale binary will fail silently.
    """
    try:
        log.info("Checking yt-dlp update…")
        yt_dlp.update.update_self(yt_dlp.update.UpdateTarget.NIGHTLY)
        log.info("yt-dlp update check complete")
    except Exception:
        log.warning("yt-dlp update failed (non-fatal)", exc_info=True)


# ===================================================================
# ffmpeg Detection
# ===================================================================


def check_ffmpeg() -> bool:
    """Detect ffmpeg on startup and warn if missing."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n", 1)[0] or "unknown"
            log.info("ffmpeg detected: %s", version_line)
            return True
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    log.warning(
        "ffmpeg not found — some formats require ffmpeg for merging and will fail"
    )
    return False


# ===================================================================
# Deno Runtime Check (D-12)
# ===================================================================


def check_deno() -> bool:
    """Verify Deno >= 2.0.0 is available (required for yt-dlp JS runtime)."""
    try:
        result = subprocess.run(
            ["deno", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            first_line = result.stdout.split("\n", 1)[0] or ""
            parts = first_line.split()
            if len(parts) >= 2:
                ver = parts[1]
                major = ver.split(".")[0]
                if major.isdigit() and int(major) >= 2:
                    log.info("Deno detected: %s", ver)
                    return True
                log.warning("Deno version %s < 2.0.0 — JS runtime may be degraded", ver)
                return False
    except FileNotFoundError:
        pass
    log.warning("Deno not found — yt-dlp will use bundled JS runtime (may be slower)")
    return False


# ===================================================================
# Temp File Management (D-06, D-07)
# ===================================================================


def create_temp_dir() -> Path:
    """Create a per-request isolated temporary directory (D-06)."""
    return Path(tempfile.mkdtemp(prefix="ytdl_"))


def _cleanup_sweep() -> None:
    """Daemon thread body — sweep & remove expired temp dirs every 5 min."""
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        try:
            now = time.time()
            tmp_root = Path(tempfile.gettempdir())
            for entry in tmp_root.glob("ytdl_*"):
                if not entry.is_dir():
                    continue
                try:
                    mtime = entry.stat().st_mtime
                    if now - mtime > TEMP_TTL_SECONDS:
                        shutil.rmtree(entry, ignore_errors=True)
                        log.debug("Cleaned up expired temp dir: %s", entry)
                except (OSError, FileNotFoundError):
                    pass
        except Exception:
            log.warning("Cleanup sweep error", exc_info=True)


def start_cleanup_daemon() -> None:
    """Start the background cleanup daemon thread (D-07)."""
    daemon = threading.Thread(
        target=_cleanup_sweep, daemon=True, name="cleanup-daemon"
    )
    daemon.start()
    log.info(
        "Temp file cleanup daemon started (TTL=%ds, interval=%ds)",
        TEMP_TTL_SECONDS,
        CLEANUP_INTERVAL_SECONDS,
    )


# ===================================================================
# URL Validation (D-08)
# ===================================================================

# Matches youtube.com/watch?v=VIDEO_ID or youtu.be/VIDEO_ID
# VIDEO_ID is exactly 11 characters of [A-Za-z0-9_-]
_YOUTUBE_RE = re.compile(
    r"^(https?://)?"
    r"(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/)"
    r"[A-Za-z0-9_-]{11}"
    r"(&[\w%+-]+=[\w%+-]*)*$"
)


def is_valid_youtube_url(url: str | None) -> bool:
    """Return True iff *url* matches a valid YouTube video URL (D-08)."""
    if not url or not isinstance(url, str):
        return False
    return bool(_YOUTUBE_RE.match(url.strip()))


# ===================================================================
# yt-dlp Options Helpers (D-09, D-10, D-11)
# ===================================================================


def _base_ydl_opts() -> dict:
    """Common options shared by info and download operations."""
    return {
        "extractors": ["youtube"],       # D-10: youtube only
        "quiet": True,
        "no_warnings": False,
    }


def _download_opts(temp_dir: Path, format_id: str = "best") -> dict:
    """Options for downloading a video to an isolated temp dir.

    The ``outtmpl`` is hardcoded (D-09) — no user input reaches the path
    template, preventing path traversal.
    """
    return {
        **_base_ydl_opts(),
        "outtmpl": str(temp_dir / "%(id)s.%(ext)s"),  # D-09
        "format": format_id,
        "restrictfilenames": True,
        "noprogress": True,
    }


# ===================================================================
# Error Handling (D-13, D-14)
# ===================================================================


class AppError(Exception):
    """Application-level error with HTTP status code and user-facing message."""

    def __init__(self, message: str, status_code: int = 400, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def _map_ytdlp_error(error: Exception) -> AppError:
    """Map a yt-dlp exception to a user-friendly AppError (D-14)."""
    msg = str(error).lower()

    # ERR-02: Unavailable / deleted / private video
    if any(term in msg for term in (
        "video unavailable",
        "private video",
        "removed video",
        "this video is unavailable",
        "uploader has not made this video available",
        "video removed",
        "content is not available",
        "unavailable",
        "this video is private",
    )):
        return AppError("This video is unavailable or has been removed.", 404)

    # ERR-01: Invalid video ID / unsupported URL
    if any(term in msg for term in (
        "unsupported url",
        "incompatible",
        "no video id",
        "invalid video id",
    )):
        return AppError("Invalid YouTube video ID or URL.", 400)

    # Rate limiting (ERR-03)
    if any(term in msg for term in ("rate limit", "too many requests", "429")):
        return AppError(
            "YouTube rate limit reached. Please wait a moment and try again.", 429
        )

    # ffmpeg missing (ERR-03)
    if any(term in msg for term in ("ffmpeg", "ffprobe", "mux", "postprocessing")):
        return AppError(
            "This format requires ffmpeg for merging, but ffmpeg is not installed. "
            "Please select a single-stream format or install ffmpeg.",
            500,
        )

    # Generic / catch-all (ERR-03)
    return AppError(
        "Failed to process the video. "
        "The download service may be temporarily unavailable. Please try again later.",
        500,
    )


# ---- Global Flask error handlers (D-13) ----


@app.errorhandler(400)
def _handle_bad_request(exc):
    return jsonify(error="Bad Request", message=str(exc.description), status=400), 400


@app.errorhandler(404)
def _handle_not_found(exc):
    return jsonify(error="Not Found", message=str(exc.description), status=404), 404


@app.errorhandler(500)
def _handle_internal_error(exc):
    log.exception("Unhandled server error")
    return jsonify(
        error="Internal Server Error",
        message="An unexpected error occurred. Please try again.",
        status=500,
    ), 500


@app.errorhandler(AppError)
def _handle_app_error(exc: AppError):
    payload = {"error": exc.message, "status": exc.status_code}
    if exc.details:
        payload["details"] = exc.details
    return jsonify(payload), exc.status_code


@app.errorhandler(HTTPException)
def _handle_http_exception(exc: HTTPException):
    """Catch-all for Flask/Werkzeug HTTP exceptions (405, 413, etc.).

    Flask defaults to HTML for these; this handler ensures JSON output.
    """
    return jsonify(
        error=exc.name,
        message=str(exc.description) if hasattr(exc, "description") else str(exc),
        status=exc.code,
    ), exc.code


# ===================================================================
# Routes
# ===================================================================


@app.route("/health", methods=["GET"])
def health():
    """Health-check endpoint returning service status JSON."""
    return jsonify(service="YouTube Video Downloader", status="running", version="1.0.0")


@app.route("/", methods=["GET"])
def index():
    """Serve the single-page frontend application."""
    try:
        return render_template("index.html")
    except Exception:
        return jsonify(service="YouTube Video Downloader", status="running", version="1.0.0")


# ===================================================================
# Task 1 — POST /info
# ===================================================================


@app.route("/info", methods=["POST"])
def get_info():
    """Fetch video metadata and list available formats (Task 1).

    Request:  ``{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}``
    Response: JSON with ``title``, ``formats``, ``duration``, ``thumbnail_url``.
    """
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        raise AppError("Missing required field: url", 400)

    url = data["url"].strip()

    if not is_valid_youtube_url(url):
        raise AppError(
            "Invalid YouTube URL. Must be a youtube.com/watch?v=… or youtu.be/… link.",
            400,
        )

    # ---- fetch info via yt-dlp --------------------------------------------
    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        cause = getattr(exc, "cause", exc)
        raise _map_ytdlp_error(cause if isinstance(cause, yt_dlp.utils.ExtractorError) else exc) from exc  # noqa: B907
    except yt_dlp.utils.ExtractorError as exc:
        raise _map_ytdlp_error(exc) from exc
    except Exception as exc:
        log.exception("Unexpected error fetching info for %s", url)
        raise AppError(
            "An unexpected error occurred while fetching video information.", 500
        ) from exc

    # ---- build format list -------------------------------------------------
    seen: set[str] = set()
    formats_out: list[dict] = []

    for f in info.get("formats", []):
        fid = f.get("format_id", "")
        if not fid or fid in seen:
            continue
        seen.add(fid)

        height = f.get("height")
        width = f.get("width")
        filesize = f.get("filesize") or f.get("filesize_approx")
        ext = f.get("ext", "mp4")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")

        if height:
            label = f"{height}p" if not width else f"{width}x{height}"
        elif acodec != "none" and vcodec == "none":
            label = "audio only"
        else:
            label = f"unknown ({fid})"

        note = f.get("format_note", "")
        if note:
            label = f"{label} ({note})"

        formats_out.append(
            {
                "format_id": fid,
                "quality": label,
                "file_size": filesize,
                "ext": ext,
                "has_video": vcodec != "none",
                "has_audio": acodec != "none",
            }
        )

    return jsonify(
        {
            "title": info.get("title", "Unknown"),
            "formats": formats_out,
            "duration": info.get("duration"),
            "thumbnail_url": info.get("thumbnail"),
            "url": url,
        }
    )


# ===================================================================
# Task 2 — POST /download
# ===================================================================


@app.route("/download", methods=["POST"])
def download_video():
    """Download a video in the requested format and stream the file (Task 2).

    Request:  ``{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "format_id": "18"}``
    Response: Streaming MP4 file attachment.
    """
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        raise AppError("Missing required field: url", 400)

    url = data["url"].strip()
    format_id = (data.get("format_id") or "").strip()

    # ---- validate ------------------------------------------------
    if not is_valid_youtube_url(url):
        raise AppError(
            "Invalid YouTube URL. Must be a youtube.com/watch?v=… or youtu.be/… link.",
            400,
        )

    if not format_id:
        raise AppError("Missing required field: format_id", 400)

    # ---- fetch info to validate format_id (T-02-02) --------------
    temp_dir = create_temp_dir()  # D-06

    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        available_ids = {f.get("format_id") for f in info.get("formats", [])}
        if format_id not in available_ids:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise AppError(
                f"Invalid format_id: {format_id!r}. "
                f"Available formats: {', '.join(sorted(available_ids, key=lambda x: (x.isdigit(), x)))}",  # noqa: B907
                400,
            )

        # ---- download the selected format --------------------------
        selected = next(
            (f for f in info.get("formats", []) if f.get("format_id") == format_id),
            {},
        )
        ext = selected.get("ext", "mp4")

        opts = _download_opts(temp_dir, format_id)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        downloaded = list(temp_dir.glob("*"))
        if not downloaded:
            raise AppError("Download completed but output file not found.", 500)

        download_path = str(downloaded[0])
        title = info.get("title", info.get("id", "video"))
        safe_filename = re.sub(r"[^\w\s.-]", "", f"{title}.{ext}")

        def _generate() -> typing.Generator[bytes, None, None]:
            """Stream the file in CHUNK_SIZE pieces (D-05)."""
            with open(download_path, "rb") as fh:
                while True:
                    chunk = fh.read(CHUNK_SIZE)  # D-05
                    if not chunk:
                        break
                    yield chunk

        return Response(
            _generate(),
            mimetype="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
        )

    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        cause = getattr(exc, "cause", exc)
        raise _map_ytdlp_error(
            cause if isinstance(cause, yt_dlp.utils.ExtractorError) else exc
        ) from exc
    except yt_dlp.utils.ExtractorError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise _map_ytdlp_error(exc) from exc
    except AppError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        log.exception("Unexpected error downloading %s", url)
        raise AppError(
            "An unexpected error occurred during download. Please try again.", 500
        ) from exc


# ===================================================================
# Task 3 — POST /download/start (Async Background Download)
# ===================================================================


@app.route("/download/start", methods=["POST"])
def download_start():
    """Start an async background download and return a download_id for progress tracking.

    Request:  ``{"url": "...", "format_id": "..."}``
    Response: ``{"download_id": "uuid4"}`` with status 202.
    """
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        raise AppError("Missing required field: url", 400)

    url = data["url"].strip()
    format_id = (data.get("format_id") or "").strip()

    if not is_valid_youtube_url(url):
        raise AppError(
            "Invalid YouTube URL. Must be a youtube.com/watch?v=… or youtu.be/… link.",
            400,
        )

    if not format_id:
        raise AppError("Missing required field: format_id", 400)

    # Validate format_id against video info
    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        cause = getattr(exc, "cause", exc)
        raise _map_ytdlp_error(
            cause if isinstance(cause, yt_dlp.utils.ExtractorError) else exc
        ) from exc
    except yt_dlp.utils.ExtractorError as exc:
        raise _map_ytdlp_error(exc) from exc
    except Exception as exc:
        log.exception("Unexpected error fetching info for /download/start")
        raise AppError(
            "An unexpected error occurred while fetching video information.", 500
        ) from exc

    available_ids = {f.get("format_id") for f in info.get("formats", [])}
    if format_id not in available_ids:
        raise AppError(
            f"Invalid format_id: {format_id!r}. "
            f"Available formats: {', '.join(sorted(available_ids, key=lambda x: (x.isdigit(), x)))}",
            400,
        )

    download_id = str(uuid.uuid4())

    with _downloads_lock:
        _download_tasks[download_id] = _DownloadState.initial()

    thread = threading.Thread(
        target=_background_download,
        args=(download_id, url, format_id),
        daemon=True,
    )
    thread.start()

    return jsonify({"download_id": download_id}), 202


# ===================================================================
# Task 4 — GET /download/progress/<download_id>
# ===================================================================


@app.route("/download/progress/<download_id>", methods=["GET"])
def download_progress(download_id: str):
    """Return current progress for a background download task.

    Response: JSON with status, percent, speed, eta, downloaded_bytes, total_bytes.
    """
    with _downloads_lock:
        state = _download_tasks.get(download_id)

    if state is None:
        return jsonify({"error": "Download not found", "status": 404}), 404

    # Return a safe subset of state (exclude internal fields like file_path)
    result = {
        "status": state["status"],
        "percent": round(state["percent"], 1),
        "speed": int(state["speed"]) if state["speed"] is not None else None,
        "eta": int(state["eta"]) if state["eta"] is not None else None,
        "downloaded_bytes": state["downloaded_bytes"],
        "total_bytes": state["total_bytes"],
    }

    if state["status"] == "error" and state["error_message"]:
        result["error_message"] = state["error_message"]

    if state["status"] == "completed":
        result["filename"] = state["filename"]

    return jsonify(result)


# ===================================================================
# Task 5 — GET /download/result/<download_id>
# ===================================================================


@app.route("/download/result/<download_id>", methods=["GET"])
def download_result(download_id: str):
    """Stream the completed download file to the browser.

    Response: Streaming file attachment (same pattern as POST /download).
    """
    with _downloads_lock:
        state = _download_tasks.get(download_id)

    if state is None:
        return jsonify({"error": "Download not found", "status": 404}), 404

    if state["status"] != "completed":
        return jsonify({"error": "Download not yet complete", "status": 400}), 400

    file_path = state["file_path"]
    filename = state["filename"] or "video.mp4"

    def _generate() -> typing.Generator[bytes, None, None]:
        with open(file_path, "rb") as fh:
            while True:
                chunk = fh.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    return Response(
        _generate(),
        mimetype="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===================================================================
# Startup
# ===================================================================


def startup() -> None:
    """Run startup checks and launch background services."""
    # yt-dlp auto-update
    update_yt_dlp()
    # Environment checks
    check_ffmpeg()
    check_deno()
    # Background daemons
    start_cleanup_daemon()

    log.info("=" * 50)
    log.info("YouTube Video Downloader ready on http://0.0.0.0:5000")
    log.info("=" * 50)


if __name__ == "__main__":
    startup()
    app.run(host="0.0.0.0", port=5000, debug=True)
