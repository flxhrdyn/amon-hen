"""Audio extraction from video files using FFmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from amonhen.decode import _ffmpeg


def extract_audio_pcm(
    video_path: str | Path,
    sample_rate: int = 16000,
) -> np.ndarray | None:
    """Extract 16kHz mono PCM float32 audio from a video file.

    Returns None if the file does not exist, has no audio stream, or decoding fails.
    """
    path = Path(video_path)
    if not path.exists():
        return None

    ffmpeg = _ffmpeg()
    # Extract mono 16-bit signed little-endian PCM audio at sample_rate directly to pipe stdout
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "pipe:1",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    raw_bytes = proc.stdout
    if not raw_bytes:
        return None

    audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
    if len(audio_int16) == 0:
        return None

    return (audio_int16.astype(np.float32) / 32768.0).copy()
