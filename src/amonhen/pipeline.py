"""The only module that knows the order of operations.

Everything below this layer is independent: decode does not know about
embeddings, encode does not know about video, store does not know where
its vectors came from. The cost of that isolation is paid here, once.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from amonhen import decode
from amonhen.model_registry import DEFAULT_MODEL
from amonhen.progress import NullReporter, Reporter
from amonhen.sample import build_sampler
from amonhen.store import FrameRecord, Hit, Store

VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpg", ".mpeg"}


@dataclass(frozen=True)
class IndexConfig:
    fps: float = 1.0
    sampler: str = "fixed"
    batch_size: int = 16
    model_id: str = DEFAULT_MODEL.model_id


@dataclass
class IndexResult:
    videos: int = 0
    frames_decoded: int = 0
    frames_kept: int = 0
    skipped: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0


def expand_paths(paths: Iterable[str | Path]) -> list[Path]:
    resolved: list[Path] = []
    for entry in paths:
        entry = Path(entry)
        if entry.is_dir():
            resolved.extend(
                sorted(
                    child
                    for child in entry.rglob("*")
                    if child.is_file() and child.suffix.lower() in VIDEO_SUFFIXES
                )
            )
        elif entry.is_file():
            resolved.append(entry)
    return resolved


def index_videos(
    paths: Iterable[str | Path],
    store: Store,
    config: IndexConfig,
    image_encoder,
    reporter: Reporter | None = None,
    force: bool = False,
) -> IndexResult:
    reporter = reporter or NullReporter()
    sampler = build_sampler(config.sampler, fps=config.fps)
    config_hash = sampler.config_hash()
    result = IndexResult()
    run_start = time.monotonic()

    for path in expand_paths(paths):
        key = str(path)
        stat = path.stat()

        if not force and not store.needs_reindex(
            key, stat.st_size, stat.st_mtime, config_hash, config.model_id
        ):
            result.skipped.append(key)
            continue

        existing = store.video_id_for_path(key)
        if existing is not None:
            store.remove_video(existing)

        info = decode.probe(path)
        reporter.video_started(key, info.duration_ms)
        video_start = time.monotonic()

        video_id = store.add_video(
            path=key,
            duration_ms=info.duration_ms,
            fps=info.fps,
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
            sampler_config_hash=config_hash,
            model_id=config.model_id,
        )

        decoded = kept = 0
        pending_images: list = []
        pending_ts: list[int] = []

        def flush(video_id: int, pending_images: list, pending_ts: list[int]) -> None:
            if not pending_images:
                return
            vectors = image_encoder.embed(pending_images)
            store.add_frames(
                video_id,
                [
                    FrameRecord(ts_ms=ts, embedding=vectors[row], kept_reason=sampler.reason)
                    for row, ts in enumerate(pending_ts)
                ],
            )

        for frame in decode.iter_frames(path, fps=config.fps):
            decoded += 1
            if not sampler.keep(frame.image):
                continue
            kept += 1
            pending_images.append(frame.image)
            pending_ts.append(frame.ts_ms)
            if len(pending_images) >= config.batch_size:
                flush(video_id, pending_images, pending_ts)
                pending_images = []
                pending_ts = []
            reporter.frame_progress(decoded, kept, frame.ts_ms)

        flush(video_id, pending_images, pending_ts)

        elapsed = time.monotonic() - video_start
        reporter.video_finished(key, decoded, kept, elapsed)

        result.videos += 1
        result.frames_decoded += decoded
        result.frames_kept += kept

    result.elapsed_s = time.monotonic() - run_start
    reporter.run_finished(result.videos, result.frames_kept, result.elapsed_s)
    return result


def search(query: str, store: Store, text_encoder, limit: int = 10) -> list[Hit]:
    vector = text_encoder.embed(query)
    return store.search_vector(vector, limit=limit)
