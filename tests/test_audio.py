from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from amonhen.audio import extract_audio_pcm
from amonhen.decode import _ffmpeg


def _create_synthetic_video_with_audio(output_path: Path, duration_sec: float = 2.0) -> Path:
    ffmpeg = _ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration_sec}:size=320x240:rate=10",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration_sec}",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _create_synthetic_video_silent(output_path: Path, duration_sec: float = 1.0) -> Path:
    ffmpeg = _ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration_sec}:size=320x240:rate=10",
        "-c:v",
        "libx264",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def test_extract_audio_pcm_from_video_with_audio(tmp_path: Path):
    video_path = _create_synthetic_video_with_audio(tmp_path / "test_audio.mp4", duration_sec=2.0)
    pcm = extract_audio_pcm(video_path, sample_rate=16000)

    assert pcm is not None
    assert isinstance(pcm, np.ndarray)
    assert pcm.dtype == np.float32
    assert 30000 <= len(pcm) <= 34000
    assert np.all(pcm >= -1.0) and np.all(pcm <= 1.0)
    assert np.max(np.abs(pcm)) > 0.05


def test_extract_audio_pcm_from_silent_video(tmp_path: Path):
    video_path = _create_synthetic_video_silent(tmp_path / "test_silent.mp4", duration_sec=1.0)
    pcm = extract_audio_pcm(video_path, sample_rate=16000)

    assert pcm is None


def test_extract_audio_pcm_nonexistent_file():
    pcm = extract_audio_pcm("/nonexistent/video/path.mp4")
    assert pcm is None
