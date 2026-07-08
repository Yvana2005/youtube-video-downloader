# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for YouTube Video Downloader.

Build on Windows with:
    pyinstaller youtube-downloader.spec

Output: dist/youtube-downloader.exe

Notes:
- Bundles templates/ as data via COLLECT/EXE `datas`
- yt-dlp needs hidden imports for its extractors/plugins
- ffmpeg/deno are NOT bundled — they must be on PATH at runtime
"""

import os
from pathlib import Path

app_root = Path(SPEC_SOURCE) if "SPEC_SOURCE" in globals() else Path(os.getcwd())
templates_dir = app_root / "templates"

# Collect the templates directory as data
datas = []
if templates_dir.exists():
    datas.append((str(templates_dir), "templates"))

# Hidden imports for yt-dlp (extractors, networking, postprocessors)
hiddenimports = [
    "yt_dlp",
    "yt_dlp.extractor",
    "yt_dlp.extractor.youtube",
    "yt_dlp.postprocessor",
    "yt_dlp.compat",
    "yt_dlp.networking",
    "yt_dlp.utils",
    "yt_dlp.version",
]

a = Analysis(
    [str(app_root / "app.py")],
    pathex=[str(app_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "test",
        "pydoc",
        "doctest",
        "pdb",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="youtube-downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
