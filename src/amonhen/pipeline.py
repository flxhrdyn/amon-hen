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
from amonhen.audio import extract_audio_pcm
from amonhen.model_registry import DEFAULT_MODEL, get_model
from amonhen.progress import NullReporter, Reporter
from amonhen.sample import Sampler, build_sampler
from amonhen.segment import Segment, merge_hits
from amonhen.store import FrameRecord, Store

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
    text_encoder=None,
    transcriber=None,
    language: str = "auto",
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

        if transcriber is not None:
            pcm = extract_audio_pcm(path)
            if pcm is not None:
                speech_segs = transcriber.transcribe(pcm, language=language)
                if speech_segs:
                    store.add_speech_segments(video_id, speech_segs)

        store.mark_complete(video_id)

        baseline = compute_video_baseline(store, video_id, text_encoder=text_encoder)
        if baseline is not None:
            store.set_score_baseline(video_id, baseline)

        elapsed = time.monotonic() - video_start
        reporter.video_finished(key, decoded, stored, elapsed)

        result.videos += 1
        result.frames_decoded += decoded
        result.frames_kept += stored

    result.elapsed_s = time.monotonic() - run_start
    reporter.run_finished(result.videos, result.frames_kept, result.elapsed_s)
    return result


_PROBE_PROMPTS = (
    "a photo of something",
    "an everyday object",
    "a background scene",
    "indoor or outdoor view",
    "a general view",
)


def compute_video_baseline(
    store: Store,
    video_id: int,
    text_encoder=None,
    sample_size: int = 50,
) -> float | None:
    embeddings = store.sample_frame_embeddings(video_id, sample_size=sample_size)
    if len(embeddings) < 5:
        return None
    frame_matrix = np.stack(embeddings)

    if text_encoder is not None:
        probe_vectors = np.stack([text_encoder.embed(p) for p in _PROBE_PROMPTS])
        sims = probe_vectors @ frame_matrix.T
        mean = float(np.mean(sims))
        std = float(np.std(sims))
        return mean + 1.5 * std

    sims = frame_matrix @ frame_matrix.T
    n = sims.shape[0]
    off_diag = sims[~np.eye(n, dtype=bool)]
    if len(off_diag) == 0:
        return None
    mean = float(np.mean(off_diag))
    std = float(np.std(off_diag))
    return mean + 1.5 * std


def search(
    query: str,
    store: Store,
    text_encoder,
    limit: int = 10,
    max_gap_ms: int = 4000,
    min_score: float | None = None,
    calibrate: bool = True,
    mode: str = "hybrid",
) -> list[Segment]:
    visual_segments: list[Segment] = []

    if mode in ("visual", "hybrid"):
        vector = text_encoder.embed(query)
        candidate_k = max(limit * 8, 32)
        hits = store.search_vector(vector, limit=candidate_k)

        if hits:
            baselines = store.get_score_baselines() if calibrate else {}
            filtered_hits = []
            for hit in hits:
                threshold = min_score
                if threshold is None and calibrate:
                    threshold = baselines.get(hit.video_id)
                if threshold is not None and hit.score < threshold:
                    continue
                filtered_hits.append(hit)
            visual_segments = merge_hits(filtered_hits, max_gap_ms=max_gap_ms, limit=limit * 2)

    speech_matches = store.search_speech(query, limit=limit) if mode in ("speech", "hybrid") else []

    if not speech_matches:
        final_segments = []
        for vseg in visual_segments:
            speech_subs = store.get_speech_segments_for_range(
                vseg.video_id, vseg.start_ms, vseg.end_ms
            )
            if speech_subs:
                combined_text = " ... ".join(s.text for s in speech_subs)
                final_segments.append(
                    Segment(
                        video_id=vseg.video_id,
                        video_path=vseg.video_path,
                        start_ms=vseg.start_ms,
                        end_ms=vseg.end_ms,
                        best_ts_ms=vseg.best_ts_ms,
                        score=vseg.score,
                        frame_count=vseg.frame_count,
                        spoken_text=combined_text,
                        match_type=vseg.match_type,
                    )
                )
            else:
                final_segments.append(vseg)
        return final_segments[:limit]

    combined: list[Segment] = []
    matched_speech_ids = set()

    for vseg in visual_segments:
        overlapping_speech = [
            sm
            for sm in speech_matches
            if sm.video_id == vseg.video_id
            and not (sm.end_ms < vseg.start_ms or sm.start_ms > vseg.end_ms)
        ]
        if overlapping_speech:
            combined_text = " ... ".join(sm.text for sm in overlapping_speech)
            combined.append(
                Segment(
                    video_id=vseg.video_id,
                    video_path=vseg.video_path,
                    start_ms=min(vseg.start_ms, min(sm.start_ms for sm in overlapping_speech)),
                    end_ms=max(vseg.end_ms, max(sm.end_ms for sm in overlapping_speech)),
                    best_ts_ms=vseg.best_ts_ms,
                    score=min(1.0, vseg.score * 1.25),
                    frame_count=vseg.frame_count,
                    spoken_text=combined_text,
                    match_type="hybrid",
                )
            )
            for sm in overlapping_speech:
                matched_speech_ids.add((sm.video_id, sm.start_ms))
        else:
            combined.append(vseg)

    for sm in speech_matches:
        if (sm.video_id, sm.start_ms) not in matched_speech_ids:
            combined.append(
                Segment(
                    video_id=sm.video_id,
                    video_path=sm.video_path,
                    start_ms=sm.start_ms,
                    end_ms=sm.end_ms,
                    best_ts_ms=(sm.start_ms + sm.end_ms) // 2,
                    score=0.40,
                    frame_count=0,
                    spoken_text=sm.text,
                    match_type="speech",
                )
            )

    combined.sort(key=lambda s: s.score, reverse=True)
    return combined[:limit]
