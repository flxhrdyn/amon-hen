"""Temporal aggregation of raw frame hits into coherent segments.

Isolated from store and pipeline so that temporal merging rules can be
tested with pure data structures without touching database or model.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from amonhen.store import Hit


@dataclass(frozen=True)
class Segment:
    video_id: int
    video_path: str
    start_ms: int
    end_ms: int
    best_ts_ms: int
    score: float
    frame_count: int
    spoken_text: str | None = None
    match_type: str = "visual"


def merge_hits(
    hits: list[Hit],
    max_gap_ms: int = 4000,
    limit: int = 10,
) -> list[Segment]:
    if not hits:
        return []

    # Group hits by video
    by_video: dict[int, list[Hit]] = defaultdict(list)
    for hit in hits:
        by_video[hit.video_id].append(hit)

    merged_segments: list[Segment] = []

    for video_id, video_hits in by_video.items():
        sorted_hits = sorted(video_hits, key=lambda h: h.ts_ms)
        path = sorted_hits[0].video_path

        current_start = sorted_hits[0].ts_ms
        current_end = sorted_hits[0].ts_ms
        current_best_ts = sorted_hits[0].ts_ms
        current_best_score = sorted_hits[0].score
        current_count = 1

        for hit in sorted_hits[1:]:
            if hit.ts_ms - current_end <= max_gap_ms:
                current_end = hit.ts_ms
                current_count += 1
                if hit.score > current_best_score:
                    current_best_score = hit.score
                    current_best_ts = hit.ts_ms
            else:
                merged_segments.append(
                    Segment(
                        video_id=video_id,
                        video_path=path,
                        start_ms=current_start,
                        end_ms=current_end,
                        best_ts_ms=current_best_ts,
                        score=current_best_score,
                        frame_count=current_count,
                    )
                )
                current_start = hit.ts_ms
                current_end = hit.ts_ms
                current_best_ts = hit.ts_ms
                current_best_score = hit.score
                current_count = 1

        merged_segments.append(
            Segment(
                video_id=video_id,
                video_path=path,
                start_ms=current_start,
                end_ms=current_end,
                best_ts_ms=current_best_ts,
                score=current_best_score,
                frame_count=current_count,
            )
        )

    merged_segments.sort(key=lambda s: s.score, reverse=True)
    return merged_segments[:limit]
