from pathlib import Path

import numpy as np
import pytest

from amonhen.pipeline import (
    IndexConfig,
    compute_video_baseline,
    expand_paths,
    index_videos,
    search,
)
from amonhen.progress import RecordingReporter
from amonhen.store import FrameRecord, Store

DIM = 8


class StubEncoder:
    """Maps a frame to a basis vector chosen by its mean pixel value.

    Deterministic and cheap, so the pipeline can be exercised end to end
    without ONNX or a real model.
    """

    def __init__(self, embed_dim: int = DIM):
        self.embed_dim = embed_dim
        self.batch_sizes: list[int] = []

    def embed(self, images):
        if not images:
            return np.zeros((0, self.embed_dim), dtype=np.float32)
        self.batch_sizes.append(len(images))
        out = np.zeros((len(images), self.embed_dim), dtype=np.float32)
        for row, image in enumerate(images):
            out[row, int(image.mean()) % self.embed_dim] = 1.0
        return out


class StubTextEncoder:
    def __init__(self, index: int, embed_dim: int = DIM):
        self.index = index
        self.embed_dim = embed_dim

    def embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.embed_dim, dtype=np.float32)
        vector[self.index] = 1.0
        return vector


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "index.db", embed_dim=DIM) as store:
        yield store


def test_index_writes_frames_for_a_real_video(store, sample_video):
    result = index_videos(
        [sample_video], store, IndexConfig(fps=2.0), StubEncoder()
    )

    assert result.videos == 1
    assert result.frames_kept > 0
    assert store.stats()["frames"] == result.frames_kept


def test_index_batches_frames_instead_of_encoding_one_at_a_time(store, sample_video):
    encoder = StubEncoder()

    index_videos([sample_video], store, IndexConfig(fps=2.0, batch_size=4), encoder)

    assert encoder.batch_sizes
    assert max(encoder.batch_sizes) <= 4
    assert max(encoder.batch_sizes) > 1


def test_reindexing_an_unchanged_video_is_skipped(store, sample_video):
    config = IndexConfig(fps=2.0)
    index_videos([sample_video], store, config, StubEncoder())

    second = index_videos([sample_video], store, config, StubEncoder())

    assert second.videos == 0
    assert second.skipped == [sample_video]


def test_force_reindexes_and_does_not_duplicate_frames(store, sample_video):
    config = IndexConfig(fps=2.0)
    first = index_videos([sample_video], store, config, StubEncoder())

    index_videos([sample_video], store, config, StubEncoder(), force=True)

    assert store.stats()["videos"] == 1
    assert store.stats()["frames"] == first.frames_kept


def test_changing_fps_forces_a_reindex(store, sample_video):
    index_videos([sample_video], store, IndexConfig(fps=2.0), StubEncoder())

    result = index_videos([sample_video], store, IndexConfig(fps=4.0), StubEncoder())

    assert result.videos == 1
    assert store.stats()["videos"] == 1


def test_reporter_receives_start_and_finish_events(store, sample_video):
    reporter = RecordingReporter()

    index_videos([sample_video], store, IndexConfig(fps=2.0), StubEncoder(), reporter)

    names = [event[0] for event in reporter.events]
    assert names[0] == "video_started"
    assert "video_finished" in names
    assert names[-1] == "run_finished"


def test_search_returns_hits_ordered_by_score(store, sample_video):
    index_videos([sample_video], store, IndexConfig(fps=2.0), StubEncoder())

    segments = search(
        "anything", store, StubTextEncoder(index=0), limit=5, calibrate=False
    )

    scores = [seg.score for seg in segments]
    assert scores == sorted(scores, reverse=True)
    assert all(seg.video_path == sample_video for seg in segments)


class ConstantEncoder:
    """Every frame maps to the same embedding, to exercise the dedup gate."""

    embed_dim = DIM

    def embed(self, images):
        return np.tile(np.eye(1, self.embed_dim, dtype=np.float32), (len(images), 1))


def test_embedding_dedup_gate_drops_near_duplicate_embeddings(store, sample_video):
    result = index_videos(
        [sample_video],
        store,
        IndexConfig(fps=2.0, embed_dedup_threshold=0.99),
        ConstantEncoder(),
    )

    assert result.frames_kept == 1
    assert store.stats()["frames"] == 1


def test_embedding_dedup_gate_disabled_by_default(store, sample_video):
    result = index_videos([sample_video], store, IndexConfig(fps=2.0), ConstantEncoder())

    assert result.frames_kept > 1


class ExplodingEncoder(StubEncoder):
    """Fails partway through a video, the way Ctrl-C would."""

    def __init__(self, fail_after: int = 1):
        super().__init__()
        self.fail_after = fail_after
        self.calls = 0

    def embed(self, images):
        self.calls += 1
        if self.calls > self.fail_after:
            raise KeyboardInterrupt("interrupted")
        return super().embed(images)


def test_an_interrupted_video_is_reindexed_not_skipped(store, sample_video):
    """A half-written video must never look complete to the next run."""
    with pytest.raises(KeyboardInterrupt):
        index_videos(
            [sample_video], store, IndexConfig(fps=5.0, batch_size=4), ExplodingEncoder()
        )

    partial = store.stats()["frames"]
    result = index_videos([sample_video], store, IndexConfig(fps=5.0, batch_size=4), StubEncoder())

    assert result.skipped == []
    assert store.stats()["frames"] > partial


def test_the_same_file_is_not_indexed_twice_under_different_spellings(
    store, sample_video, monkeypatch
):
    config = IndexConfig(fps=2.0)
    index_videos([sample_video], store, config, StubEncoder())

    monkeypatch.chdir(Path(sample_video).parent)
    result = index_videos([Path(sample_video).name], store, config, StubEncoder())

    assert store.stats()["videos"] == 1
    assert result.skipped != []


def test_changing_embed_dedup_forces_a_reindex(store, sample_video):
    """A flag that changes which frames get stored must invalidate the index."""
    index_videos([sample_video], store, IndexConfig(fps=5.0), StubEncoder())

    result = index_videos(
        [sample_video],
        store,
        IndexConfig(fps=5.0, embed_dedup_threshold=0.99),
        StubEncoder(),
    )

    assert result.videos == 1
    assert result.skipped == []


def test_sampler_state_does_not_leak_between_videos(store, tmp_path, static_video):
    """Video 2's first frame must be judged on its own, not against video 1.

    Each static video collapses to exactly one kept frame, so two of them
    must yield two. A shared sampler would compare video 2's opening frame
    against video 1's and silently drop it.
    """
    import shutil

    second = tmp_path / "second.mp4"
    shutil.copy(static_video, second)

    result = index_videos(
        [static_video, second], store, IndexConfig(fps=5.0, sampler="adaptive"), StubEncoder()
    )

    assert result.frames_kept == 2


def test_adaptive_sampler_keeps_no_more_frames_than_fixed(store, sample_video, tmp_path):
    fixed_result = index_videos(
        [sample_video], store, IndexConfig(fps=5.0, sampler="fixed"), StubEncoder()
    )

    with Store(tmp_path / "adaptive.db", embed_dim=DIM) as adaptive_store:
        adaptive_result = index_videos(
            [sample_video],
            adaptive_store,
            IndexConfig(fps=5.0, sampler="adaptive"),
            StubEncoder(),
        )

    assert adaptive_result.frames_kept <= fixed_result.frames_kept


def test_expand_paths_finds_videos_in_a_directory(tmp_path, sample_video):
    import shutil

    shutil.copy(sample_video, tmp_path / "one.mp4")
    shutil.copy(sample_video, tmp_path / "two.mkv")
    (tmp_path / "notes.txt").write_text("ignore me")

    found = sorted(path.name for path in expand_paths([tmp_path]))

    assert found == ["one.mp4", "two.mkv"]


def test_search_returns_segments_with_merging(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    # Add frames with unit vectors
    f1 = FrameRecord(
        ts_ms=1000,
        embedding=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        kept_reason="fixed",
    )
    f2 = FrameRecord(
        ts_ms=2000,
        embedding=np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32),
        kept_reason="fixed",
    )
    store.add_frames(v1, [f1, f2])
    store.mark_complete(v1)

    class FakeTextEncoder:
        def embed(self, text: str):
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    segments = search(
        "query", store, FakeTextEncoder(), limit=5, max_gap_ms=2000, calibrate=False
    )
    assert len(segments) == 1
    assert segments[0].start_ms == 1000
    assert segments[0].end_ms == 2000
    assert segments[0].frame_count == 2
    store.close()


def test_search_filters_below_min_score(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    f1 = FrameRecord(
        ts_ms=1000,
        embedding=np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32),
        kept_reason="fixed",
    )
    store.add_frames(v1, [f1])
    store.mark_complete(v1)

    class FakeTextEncoder:
        def embed(self, text: str):
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    segments = search(
        "query", store, FakeTextEncoder(), limit=5, min_score=0.9, calibrate=False
    )
    assert segments == []
    store.close()


def test_search_filters_below_baseline_when_calibrated(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    store.set_score_baseline(v1, 0.8)
    f1 = FrameRecord(
        ts_ms=1000,
        embedding=np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32),
        kept_reason="fixed",
    )
    store.add_frames(v1, [f1])
    store.mark_complete(v1)

    class FakeTextEncoder:
        def embed(self, text: str):
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    segments = search("query", store, FakeTextEncoder(), limit=5, calibrate=True)
    assert segments == []

    segments_uncalibrated = search(
        "query", store, FakeTextEncoder(), limit=5, calibrate=False
    )
    assert len(segments_uncalibrated) == 1
    store.close()


def test_compute_video_baseline_insufficient_frames(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    records = [
        FrameRecord(
            ts_ms=i * 1000,
            embedding=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
            kept_reason="fixed",
        )
        for i in range(3)
    ]
    store.add_frames(v1, records)
    store.mark_complete(v1)

    baseline = compute_video_baseline(store, v1)
    assert baseline is None
    store.close()


def test_compute_video_baseline_calculates_mean_and_std(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    embeddings = [
        np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32),
        np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
        np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
    ]
    records = [
        FrameRecord(ts_ms=i * 1000, embedding=emb, kept_reason="fixed")
        for i, emb in enumerate(embeddings)
    ]
    store.add_frames(v1, records)
    store.mark_complete(v1)

    baseline = compute_video_baseline(store, v1, sample_size=10)
    assert baseline is not None
    assert isinstance(baseline, float)
    store.close()


def test_index_videos_computes_and_sets_score_baseline(store, sample_video):
    index_videos([sample_video], store, IndexConfig(fps=5.0), StubEncoder())

    baselines = store.get_score_baselines()
    video_id = store.video_id_for_path(sample_video)
    if store.stats()["frames"] >= 5:
        assert video_id in baselines
        assert isinstance(baselines[video_id], float)
