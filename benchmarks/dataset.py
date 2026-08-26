"""Benchmark dataset parsing and synthetic test dataset generator."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg


@dataclass(frozen=True)
class AnnotationItem:
    query: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class VideoDatasetItem:
    video_path: Path
    duration_s: float
    annotations: list[AnnotationItem]


def load_dataset(json_path: Path | str) -> list[VideoDatasetItem]:
    path = Path(json_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    items: list[VideoDatasetItem] = []
    base_dir = path.parent
    for entry in raw:
        video_p = Path(entry["video_path"])
        if not video_p.is_absolute():
            video_p = (base_dir / video_p).resolve()
        annotations = [
            AnnotationItem(
                query=ann["query"],
                start_s=float(ann["start_s"]),
                end_s=float(ann["end_s"]),
            )
            for ann in entry.get("annotations", [])
        ]
        items.append(
            VideoDatasetItem(
                video_path=video_p,
                duration_s=float(entry["duration_s"]),
                annotations=annotations,
            )
        )
    return items


def generate_synthetic_benchmark(
    output_dir: Path | str, count: int = 2
) -> list[VideoDatasetItem]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    items: list[VideoDatasetItem] = []
    for i in range(count):
        video_path = out_dir / f"synth_{i:02d}.mp4"
        duration_s = 4.0
        subprocess.run(
            [
                ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc=size=64x64:rate=10:duration={duration_s}",
                "-pix_fmt",
                "yuv420p",
                str(video_path),
            ],
            check=True,
        )
        annotations = [
            AnnotationItem(
                query="a test pattern with color bars",
                start_s=0.5,
                end_s=3.5,
            )
        ]
        items.append(
            VideoDatasetItem(
                video_path=video_path,
                duration_s=duration_s,
                annotations=annotations,
            )
        )

    # Save accompanying annotations JSON
    manifest = [
        {
            "video_path": str(item.video_path.relative_to(out_dir)),
            "duration_s": item.duration_s,
            "annotations": [
                {
                    "query": a.query,
                    "start_s": a.start_s,
                    "end_s": a.end_s,
                }
                for a in item.annotations
            ],
        }
        for item in items
    ]
    (out_dir / "annotations.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return items
