from __future__ import annotations

from pathlib import Path

from amonhen.store import SpeechSegment, Store


def test_speech_segments_crud_and_fts_search(tmp_path: Path):
    db_path = tmp_path / "test_speech.db"
    store = Store(db_path, embed_dim=512)

    v1_id = store.add_video(
        path="/videos/speech_sample.mp4",
        duration_ms=60000,
        fps=30.0,
        size_bytes=1024,
        mtime=1.0,
        sampler_config_hash="abc",
        model_id="mobileclip2-s0",
    )
    store.mark_complete(v1_id)

    segments = [
        SpeechSegment(start_ms=1000, end_ms=4500, text="Hello and welcome to the demonstration"),
        SpeechSegment(start_ms=5000, end_ms=9000, text="Today we are tracking a red sports car"),
        SpeechSegment(
            start_ms=10000, end_ms=14000, text="A person is walking with an umbrella in the rain"
        ),
    ]

    store.add_speech_segments(v1_id, segments)

    # Search for "umbrella"
    matches = store.search_speech("umbrella", limit=5)
    assert len(matches) == 1
    assert matches[0].video_id == v1_id
    assert matches[0].start_ms == 10000
    assert matches[0].end_ms == 14000
    assert "umbrella in the rain" in matches[0].text
    assert matches[0].rank_score is not None

    # Search for "sports car"
    matches_car = store.search_speech("sports car", limit=5)
    assert len(matches_car) == 1
    assert matches_car[0].start_ms == 5000
    assert "red sports car" in matches_car[0].text

    # Search for non-existent phrase
    matches_none = store.search_speech("spaceship landing", limit=5)
    assert len(matches_none) == 0

    # Get overlapping speech segments
    overlap = store.get_speech_segments_for_range(v1_id, start_ms=4000, end_ms=6000)
    # Overlaps segment 1 (1000-4500) and segment 2 (5000-9000)
    assert len(overlap) == 2

    # Remove video cleans up speech
    store.remove_video(v1_id)
    assert len(store.search_speech("umbrella")) == 0

    store.close()
