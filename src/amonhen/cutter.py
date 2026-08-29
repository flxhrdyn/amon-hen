"""Instant video segment exporter using FFmpeg stream-copy and re-encoding."""

from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg

from amonhen.decode import FFmpegError


def parse_timestamp(val: str | float | int) -> int:
    """Parse time representations into integer milliseconds.

    Accepts:
      - Integers or floats: 10 -> 10000, 75.5 -> 75500
      - String seconds: "75.5" -> 75500
      - String MM:SS or MM:SS.s: "01:15.5" -> 75500
      - String HH:MM:SS or HH:MM:SS.s: "00:01:15" -> 75000
    """
    if isinstance(val, (int, float)):
        if val < 0:
            raise ValueError(f"Timestamp cannot be negative: {val}")
        return int(round(val * 1000.0))

    val_str = str(val).strip()
    if not val_str:
        raise ValueError("Timestamp cannot be empty")

    if ":" in val_str:
        parts = val_str.split(":")
        if len(parts) == 2:
            try:
                minutes = float(parts[0])
                seconds = float(parts[1])
                if minutes < 0 or seconds < 0:
                    raise ValueError(f"Timestamp cannot be negative: {val}")
                return int(round((minutes * 60.0 + seconds) * 1000.0))
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {val}") from e
        elif len(parts) == 3:
            try:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                if hours < 0 or minutes < 0 or seconds < 0:
                    raise ValueError(f"Timestamp cannot be negative: {val}")
                return int(round((hours * 3600.0 + minutes * 60.0 + seconds) * 1000.0))
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {val}") from e
        else:
            raise ValueError(f"Invalid timestamp format: {val}")

    try:
        sec = float(val_str)
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {val}") from e

    if sec < 0:
        raise ValueError(f"Timestamp cannot be negative: {val}")
    return int(round(sec * 1000.0))


def format_timestamp_tag(ms: int) -> str:
    """Format milliseconds into a safe filename tag (e.g. 01m15s or 01h02m03s)."""
    total_seconds = max(0, ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}h{minutes:02d}m{seconds:02d}s"
    return f"{minutes:02d}m{seconds:02d}s"


def generate_clip_path(
    video_path: Path | str,
    start_ms: int,
    end_ms: int,
    out_path: Path | str | None = None,
    out_dir: Path | str | None = None,
) -> Path:
    """Resolve destination clip path."""
    if out_path is not None:
        return Path(out_path)

    vpath = Path(video_path)
    stem = vpath.stem
    tag_start = format_timestamp_tag(start_ms)
    tag_end = format_timestamp_tag(end_ms)
    filename = f"{stem}_clip_{tag_start}_{tag_end}.mp4"

    directory = Path(out_dir) if out_dir is not None else Path.cwd()
    return directory / filename


def cut_video_segment(
    video_path: Path | str,
    start_ms: int,
    end_ms: int,
    out_path: Path | str | None = None,
    out_dir: Path | str | None = None,
    reencode: bool = False,
) -> Path:
    """Cut a segment from video_path and save to out_path.

    Parameters:
      video_path: Source video path.
      start_ms: Start time in milliseconds.
      end_ms: End time in milliseconds.
      out_path: Optional explicit output file path.
      out_dir: Optional output directory (used if out_path is None).
      reencode: When True, re-encodes with libx264/aac for frame-exact boundaries.
                When False, stream copies for instantaneous, lossless extraction.
    """
    src_path = Path(video_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Source video not found: {src_path}")

    if start_ms > end_ms:
        raise ValueError(f"start_ms must be less than or equal to end_ms ({start_ms} > {end_ms})")

    destination = generate_clip_path(
        src_path, start_ms=start_ms, end_ms=end_ms, out_path=out_path, out_dir=out_dir
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    start_s = f"{start_ms / 1000.0:.3f}"
    end_s = f"{end_ms / 1000.0:.3f}"
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    if reencode:
        cmd = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            start_s,
            "-to",
            end_s,
            "-i",
            str(src_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-crf",
            "20",
            "-preset",
            "fast",
            "-y",
            str(destination),
        ]
    else:
        cmd = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            start_s,
            "-to",
            end_s,
            "-i",
            str(src_path),
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            "-y",
            str(destination),
        ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(
            f"FFmpeg segment cut failed with returncode {proc.returncode}: {proc.stderr}"
        )

    return destination
