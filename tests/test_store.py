import numpy as np
import pytest

from amonhen.store import FrameRecord, IncompatibleIndexError, Store

DIM = 8


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def basis(index: int) -> np.ndarray:
    vector = np.zeros(DIM, dtype=np.float32)
    vector[index] = 1.0
    return vector


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "index.db", embed_dim=DIM) as store:
        yield store


def add_sample_video(store, path="a.mp4", ts_list=(0, 1000, 2000)):
    video_id = store.add_video(
        path=path, duration_ms=3000, fps=25.0, size_bytes=123,
        mtime=1.0, sampler_config_hash="cfg1", model_id="m1",
    )
    store.add_frames(
        video_id,
        [
            FrameRecord(ts_ms=ts, embedding=basis(i), kept_reason="fixed")
            for i, ts in enumerate(ts_list)
        ],
    )
    store.mark_complete(video_id)
    return video_id


def test_add_video_and_frames_are_counted(store):
    add_sample_video(store)
    assert store.stats() == {"videos": 1, "frames": 3, "by_reason": {"fixed": 3}}


def test_a_video_needs_reindex_until_it_is_marked_complete(store):
    video_id = store.add_video(
        path="a.mp4", duration_ms=3000, fps=25.0, size_bytes=123,
        mtime=1.0, sampler_config_hash="cfg1", model_id="m1",
    )

    assert store.needs_reindex("a.mp4", 123, 1.0, "cfg1", "m1")

    store.mark_complete(video_id)

    assert not store.needs_reindex("a.mp4", 123, 1.0, "cfg1", "m1")


def test_stats_breaks_down_frames_by_kept_reason(store):
    video_id = store.add_video(
        path="a.mp4", duration_ms=3000, fps=25.0, size_bytes=123,
        mtime=1.0, sampler_config_hash="cfg1", model_id="m1",
    )
    store.add_frames(
        video_id,
        [
            FrameRecord(ts_ms=0, embedding=basis(0), kept_reason="fixed"),
            FrameRecord(ts_ms=1000, embedding=basis(1), kept_reason="adaptive"),
            FrameRecord(ts_ms=2000, embedding=basis(2), kept_reason="adaptive"),
        ],
    )

    assert store.stats()["by_reason"] == {"fixed": 1, "adaptive": 2}


def test_search_returns_nearest_frame_first(store):
    add_sample_video(store)

    hits = store.search_vector(basis(1), limit=3)

    assert hits[0].ts_ms == 1000
    assert hits[0].video_path == "a.mp4"
    assert hits[0].score > hits[1].score


def test_search_spans_multiple_videos(store):
    add_sample_video(store, path="a.mp4")
    add_sample_video(store, path="b.mp4", ts_list=(5000, 6000, 7000))

    hits = store.search_vector(basis(0), limit=10)

    assert {hit.video_path for hit in hits} == {"a.mp4", "b.mp4"}


def test_scores_are_cosine_similarity_in_unit_range(store):
    add_sample_video(store)

    hits = store.search_vector(basis(0), limit=3)

    assert 0.99 <= hits[0].score <= 1.01
    assert all(-1.01 <= hit.score <= 1.01 for hit in hits)


def test_unchanged_video_does_not_need_reindex(store):
    add_sample_video(store)
    assert not store.needs_reindex("a.mp4", 123, 1.0, "cfg1", "m1")


def test_changed_mtime_needs_reindex(store):
    add_sample_video(store)
    assert store.needs_reindex("a.mp4", 123, 2.0, "cfg1", "m1")


def test_changed_sampler_config_needs_reindex(store):
    add_sample_video(store)
    assert store.needs_reindex("a.mp4", 123, 1.0, "cfg2", "m1")


def test_changed_model_needs_reindex(store):
    add_sample_video(store)
    assert store.needs_reindex("a.mp4", 123, 1.0, "cfg1", "m2")


def test_unknown_video_needs_reindex(store):
    assert store.needs_reindex("never-seen.mp4", 1, 1.0, "cfg1", "m1")


def test_remove_video_drops_its_frames(store):
    video_id = add_sample_video(store)

    store.remove_video(video_id)

    assert store.stats() == {"videos": 0, "frames": 0, "by_reason": {}}
    assert store.search_vector(basis(0), limit=5) == []


def test_list_videos_reports_frame_counts(store):
    add_sample_video(store)

    rows = store.list_videos()

    assert len(rows) == 1
    assert rows[0].path == "a.mp4"
    assert rows[0].frame_count == 3


def test_opening_with_a_different_dimension_is_refused(tmp_path):
    path = tmp_path / "index.db"
    with Store(path, embed_dim=DIM) as store:
        add_sample_video(store)

    with pytest.raises(IncompatibleIndexError):
        Store(path, embed_dim=DIM + 1).__enter__()


def test_set_and_get_score_baselines(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("a.mp4", 1000, 10.0, 100, 1.0, "h1", "m1")
    v2 = store.add_video("b.mp4", 1000, 10.0, 100, 1.0, "h1", "m1")

    store.set_score_baseline(v1, 0.225)
    baselines = store.get_score_baselines()

    assert baselines.get(v1) == 0.225
    assert v2 not in baselines or baselines.get(v2) is None
    store.close()


def test_sample_frame_embeddings(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("a.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    records = [
        FrameRecord(
            ts_ms=i * 1000,
            embedding=np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32),
            kept_reason="fixed",
        )
        for i in range(10)
    ]
    store.add_frames(v1, records)

    samples = store.sample_frame_embeddings(v1, sample_size=5)
    assert len(samples) == 5
    assert samples[0].shape == (4,)
    store.close()


