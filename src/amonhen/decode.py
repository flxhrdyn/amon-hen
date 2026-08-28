"""Frame extraction via an ffmpeg subprocess.

Decoding dominates indexing time, so frame thinning is pushed into
ffmpeg's own filter graph: frames dropped by `-vf fps=` are never
decoded into Python at all. Reading every frame with a capture loop and
discarding most of them in Python would do the expensive work first and
throw the result away.
"""

from __future__ import annotations

import subprocess
import tempfile
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
    # read out of ffmpeg's own stderr banner. Giving ffmpeg no output file
    # makes it print the banner and stop; asking it to write to null would
    # decode the entire video first, which probe does not need.
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(path)],
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
            duration_ms = int((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)
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


def iter_frames(path: str | Path, fps: float, info: VideoInfo | None = None) -> Iterator[Frame]:
    """Yield frames thinned to `fps`.

    Pass `info` to reuse metadata the caller has already probed, rather
    than paying for a second probe of the same file.
    """
    path = Path(path)
    info = info or probe(path)
    frame_bytes = info.width * info.height * 3

    command = [
        _ffmpeg(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vf",
        f"fps={fps}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]
    # stderr goes to a temporary file rather than a pipe: nothing reads it
    # until ffmpeg finishes, and a chatty file would otherwise fill the
    # pipe buffer and deadlock both processes.
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        assert proc.stdout is not None

        index = 0
        drained = False
        try:
            while True:
                buffer = proc.stdout.read(frame_bytes)
                if len(buffer) < frame_bytes:
                    drained = True
                    break
                # frombuffer aliases the read buffer and is read-only;
                # copy so callers get a normal, writable array.
                image = (
                    np.frombuffer(buffer, dtype=np.uint8).reshape(info.height, info.width, 3).copy()
                )
                yield Frame(ts_ms=int(round(index * 1000.0 / fps)), image=image)
                index += 1
        finally:
            proc.stdout.close()
            if not drained:
                # The consumer stopped early. ffmpeg still has work queued,
                # so end it rather than waiting on a process writing into a
                # closed pipe.
                proc.kill()
            code = proc.wait()
            if drained and code != 0:
                errors.seek(0)
                message = errors.read().decode(errors="replace").strip()
                raise FFmpegError(message or f"ffmpeg exited with {code}")
