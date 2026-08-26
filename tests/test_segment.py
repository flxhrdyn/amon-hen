from amonhen.segment import Segment, merge_hits
from amonhen.store import Hit


def test_merge_hits_empty_returns_empty():
    assert merge_hits([], max_gap_ms=4000, limit=10) == []


def test_merge_hits_single_hit_becomes_single_frame_segment():
    hit = Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.25)
    segments = merge_hits([hit], max_gap_ms=4000, limit=10)

    assert len(segments) == 1
    seg = segments[0]
    assert isinstance(seg, Segment)
    assert seg.video_id == 1
    assert seg.video_path == "/path/a.mp4"
    assert seg.start_ms == 1000
    assert seg.end_ms == 1000
    assert seg.best_ts_ms == 1000
    assert seg.score == 0.25
    assert seg.frame_count == 1


def test_merge_hits_combines_adjacent_frames_in_same_video():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.20),
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=2000, score=0.30),
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=3500, score=0.25),
    ]
    segments = merge_hits(hits, max_gap_ms=2000, limit=10)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.start_ms == 1000
    assert seg.end_ms == 3500
    assert seg.best_ts_ms == 2000
    assert seg.score == 0.30
    assert seg.frame_count == 3


def test_merge_hits_splits_when_gap_exceeds_threshold():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.20),
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=10000, score=0.35),
    ]
    segments = merge_hits(hits, max_gap_ms=4000, limit=10)

    assert len(segments) == 2
    # Highest score first
    assert segments[0].start_ms == 10000
    assert segments[0].score == 0.35
    assert segments[1].start_ms == 1000
    assert segments[1].score == 0.20


def test_merge_hits_isolates_different_videos():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.25),
        Hit(video_id=2, video_path="/path/b.mp4", ts_ms=1200, score=0.30),
    ]
    segments = merge_hits(hits, max_gap_ms=4000, limit=10)

    assert len(segments) == 2
    assert segments[0].video_id == 2
    assert segments[1].video_id == 1


def test_merge_hits_respects_limit():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=i * 10000, score=0.10 + i * 0.05)
        for i in range(10)
    ]
    segments = merge_hits(hits, max_gap_ms=2000, limit=3)
    assert len(segments) == 3
    assert segments[0].score > segments[1].score > segments[2].score
