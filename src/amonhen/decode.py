"""Frame extraction via an ffmpeg subprocess.

Decoding dominates indexing time, so frame thinning is pushed into
ffmpeg's own filter graph: frames dropped by `-vf fps=` are never
decoded into Python at all. Reading every frame with a capture loop and
discarding most of them in Python would do the expensive work first and
throw the result away.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np


class FFmpegError(RuntimeError):
    pass


@dataclass(frozen=True)
class Frame:
    ts_ms: int
    image: np.ndarray


@dataclass(frozen=True)
class VideoInfo:
    duration_ms: int
    fps: float
    width: int
    height: int


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _ffmpeg_stderr(path: Path) -> str:
    # imageio-ffmpeg ships ffmpeg but not ffprobe, so stream metadata is
    # read out of ffmpeg's own stderr banner.
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    return proc.stderr


def probe(path: str | Path) -> VideoInfo:
    path = Path(path)
    if not path.exists():
        raise FFmpegError(f"file not found: {path}")

    stderr = _ffmpeg_stderr(path)
    if "Invalid data" in stderr or "No such file" in stderr:
        raise FFmpegError(stderr.strip().splitlines()[-1] if stderr else "ffmpeg failed")

    duration_ms = 0
    fps = 0.0
    width = height = 0
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            clock = line.split("Duration:")[1].split(",")[0].strip()
            hours, minutes, seconds = clock.split(":")
            duration_ms = int(
                (int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000
            )
        if "Video:" in line:
            for part in line.split(","):
                part = part.strip()
                if part.endswith("fps"):
                    fps = float(part[:-3].strip())
                if "x" in part and width == 0:
                    left, _, right = part.partition("x")
                    if left.strip().isdigit() and right.split()[0].isdigit():
                        width = int(left.strip())
                        height = int(right.split()[0])

    if width == 0 or height == 0:
        raise FFmpegError(f"no video stream found in {path}")

    return VideoInfo(duration_ms=duration_ms, fps=fps, width=width, height=height)


def iter_frames(path: str | Path, fps: float) -> Iterator[Frame]:
    path = Path(path)
    info = probe(path)
    frame_bytes = info.width * info.height * 3
    interval_ms = int(round(1000.0 / fps))

    command = [
        _ffmpeg(), "-hide_banner", "-loglevel", "error",
        "-i", str(path),
        "-vf", f"fps={fps}",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-",
    ]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None

    index = 0
    try:
        while True:
            buffer = proc.stdout.read(frame_bytes)
            if len(buffer) < frame_bytes:
                break
            image = np.frombuffer(buffer, dtype=np.uint8).reshape(
                info.height, info.width, 3
            )
            yield Frame(ts_ms=index * interval_ms, image=image)
            index += 1
    finally:
        proc.stdout.close()
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code != 0 and index == 0:
            raise FFmpegError(stderr.strip() or f"ffmpeg exited with {code}")
