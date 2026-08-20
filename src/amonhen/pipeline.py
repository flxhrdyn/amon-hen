"""The only module that knows the order of operations.

Everything below this layer is independent: decode does not know about
embeddings, encode does not know about video, store does not know where
its vectors came from. The cost of that isolation is paid here, once.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from amonhen import decode
from amonhen.model_registry import DEFAULT_MODEL, get_model
from amonhen.progress import NullReporter, Reporter
from amonhen.sample import Sampler, build_sampler
from amonhen.store import FrameRecord, Hit, Store

VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpg", ".mpeg"}


@dataclass(frozen=True)
class IndexConfig:
    fps: float = 1.0
    sampler: str = "fixed"
    batch_size: int = 16
    model_id: str = DEFAULT_MODEL.model_id
    embed_dedup_threshold: float | None = None
    dedup_hamming_threshold: int = 4
    blur_sharpness_threshold: float | None = None


@dataclass
class IndexResult:
    videos: int = 0
    frames_decoded: int = 0
    frames_kept: int = 0
    skipped: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0


def _sampler_for(config: IndexConfig) -> Sampler:
    return build_sampler(
        config.sampler,
        fps=config.fps,
        dedup_hamming_threshold=config.dedup_hamming_threshold,
        blur_sharpness_threshold=config.blur_sharpness_threshold,
    )


def _index_config_hash(config: IndexConfig) -> str:
    """Fingerprint every setting that changes which frames end up stored.

    The sampler's own hash covers its gates, but the embedding-dedup gate
    lives here in the pipeline. Leaving it out would let a user turn it on
    and have every video silently skipped as already-indexed.

    The model's preprocessing revision is included too, so that correcting
    how frames are prepared invalidates vectors built the old way instead
    of leaving two incompatible generations mixed in one index.
    """
    sampler_hash = _sampler_for(config).config_hash()
    payload = (
        f"{sampler_hash}"
        f":embed_dedup={config.embed_dedup_threshold}"
        f":preprocess={get_model(config.model_id).preprocess_version}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def expand_paths(paths: Iterable[str | Path]) -> list[Path]:
    # Paths are resolved so that a relative and an absolute spelling of the
    # same file identify one video, not two.
    resolved: list[Path] = []
    for entry in paths:
        entry = Path(entry)
        if entry.is_dir():
            resolved.extend(
                sorted(
                    child.resolve()
                    for child in entry.rglob("*")
                    if child.is_file() and child.suffix.lower() in VIDEO_SUFFIXES
                )
            )
        elif entry.is_file():
            resolved.append(entry.resolve())
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
    reason = _sampler_for(config).reason
    config_hash = _index_config_hash(config)
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

        # Samplers carry per-video state, so each video gets its own.
        sampler = _sampler_for(config)

        decoded = stored = 0
        pending_images: list = []
        pending_ts: list[int] = []
        last_embedding: list[np.ndarray | None] = [None]

        def flush(
            video_id: int,
            pending_images: list,
            pending_ts: list[int],
            last_embedding: list[np.ndarray | None],
        ) -> int:
            if not pending_images:
                return 0
            vectors = image_encoder.embed(pending_images)
            records = []
            for row, ts in enumerate(pending_ts):
                vector = vectors[row]
                if config.embed_dedup_threshold is not None and last_embedding[0] is not None:
                    similarity = float(
                        np.dot(vector, last_embedding[0])
                        / (np.linalg.norm(vector) * np.linalg.norm(last_embedding[0]) + 1e-12)
                    )
                    if similarity >= config.embed_dedup_threshold:
                        continue
                records.append(FrameRecord(ts_ms=ts, embedding=vector, kept_reason=reason))
                last_embedding[0] = vector
            if records:
                store.add_frames(video_id, records)
            return len(records)

        for frame in decode.iter_frames(path, fps=config.fps, info=info):
            decoded += 1
            if not sampler.keep(frame.image):
                continue
            pending_images.append(frame.image)
            pending_ts.append(frame.ts_ms)
            if len(pending_images) >= config.batch_size:
                stored += flush(video_id, pending_images, pending_ts, last_embedding)
                pending_images = []
                pending_ts = []
            # Reports frames actually written, so progress and the final
            # count are the same number rather than two different ones.
            reporter.frame_progress(decoded, stored, frame.ts_ms)

        stored += flush(video_id, pending_images, pending_ts, last_embedding)
        store.mark_complete(video_id)

        elapsed = time.monotonic() - video_start
        reporter.video_finished(key, decoded, stored, elapsed)

        result.videos += 1
        result.frames_decoded += decoded
        result.frames_kept += stored

    result.elapsed_s = time.monotonic() - run_start
    reporter.run_finished(result.videos, result.frames_kept, result.elapsed_s)
    return result


def search(query: str, store: Store, text_encoder, limit: int = 10) -> list[Hit]:
    vector = text_encoder.embed(query)
    return store.search_vector(vector, limit=limit)
