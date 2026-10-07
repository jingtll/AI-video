# _ff.py — locate a full-featured ffmpeg/ffprobe across environments.
# Order: PATH → WinGet Links → WinGet Packages (Gyan.FFmpeg) → error with install hint.
import os
from pathlib import Path


def _winget_candidates():
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return []
    cands = []
    links = Path(local) / "Microsoft" / "WinGet" / "Links"
    cands.append(links / "ffmpeg.exe")
    cands.append(links / "ffprobe.exe")
    pkgs = Path(local) / "Microsoft" / "WinGet" / "Packages"
    if pkgs.exists():
        for d in pkgs.glob("Gyan.FFmpeg*"):
            for exe in d.glob("**/bin/ffmpeg.exe"):
                cands.append(exe)
            for exe in d.glob("**/bin/ffprobe.exe"):
                cands.append(exe)
    return cands


def resolve(name: str) -> str:
    import shutil
    p = shutil.which(name)
    if p:
        return p
    for c in _winget_candidates():
        if c.name == name + ".exe" and c.exists():
            return str(c)
    raise SystemExit(
        f"{name} not found. Install the FULL build (stripped IDE bundles lack libmp3lame/amix): "
        "winget install Gyan.FFmpeg -e   (then reopen the shell)"
    )


def ffmpeg() -> str:
    return resolve("ffmpeg")


def ffprobe() -> str:
    return resolve("ffprobe")
