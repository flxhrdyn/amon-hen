"""Launch media players at specific timestamps with OS fallback."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path


def build_player_command(
    video_path: Path | str,
    ts_ms: int,
    player_binary: str | None = None,
) -> list[str]:
    path_str = str(video_path)
    ts_s = f"{ts_ms / 1000.0:.1f}"

    binary = player_binary
    if binary is None:
        for candidate in ("mpv", "vlc", "ffplay"):
            if shutil.which(candidate):
                binary = candidate
                break

    if binary == "mpv":
        return ["mpv", f"--start={ts_s}", path_str]
    if binary == "vlc":
        return ["vlc", f"--start-time={ts_s}", path_str]
    if binary == "ffplay":
        return ["ffplay", "-ss", ts_s, "-autoexit", path_str]

    return [path_str]


def open_video_at(
    video_path: Path | str,
    ts_ms: int,
    player_command: str | None = None,
) -> bool:
    path = Path(video_path)
    if not path.exists():
        return False

    cmd = build_player_command(path, ts_ms, player_binary=player_command)
    try:
        if len(cmd) > 1:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        # OS Default fallback
        if platform.system() == "Windows":
            os.startfile(str(path))
            return True
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
            return True
        else:
            subprocess.Popen(["xdg-open", str(path)])
            return True
    except Exception:
        return False
