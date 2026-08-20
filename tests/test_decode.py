import numpy as np
import pytest

from amonhen.decode import FFmpegError, iter_frames, probe


def test_probe_reads_duration_and_size(sample_video):
    info = probe(sample_video)
    assert 3800 <= info.duration_ms <= 4200
    assert info.width == 32
    assert info.height == 32
    assert 9.5 <= info.fps <= 10.5


def test_iter_frames_respects_target_fps(sample_video):
    frames = list(iter_frames(sample_video, fps=2.0))
    assert 7 <= len(frames) <= 9


def test_frames_carry_rgb_images_and_rising_timestamps(sample_video):
    frames = list(iter_frames(sample_video, fps=2.0))
    first = frames[0]
    assert first.image.shape == (32, 32, 3)
    assert first.image.dtype == np.uint8
    timestamps = [f.ts_ms for f in frames]
    assert timestamps == sorted(timestamps)
    assert timestamps[0] < timestamps[-1]


def test_missing_file_raises_ffmpeg_error(tmp_path):
    with pytest.raises(FFmpegError):
        probe(tmp_path / "nope.mp4")


def test_timestamps_do_not_drift_at_awkward_frame_rates(sample_video):
    """A rounded per-frame interval accumulates error over a long video."""
    frames = list(iter_frames(sample_video, fps=3.0))

    for position, frame in enumerate(frames):
        assert abs(frame.ts_ms - round(position * 1000.0 / 3.0)) <= 1


def test_frames_are_writable(sample_video):
    """A read-only view would break any in-place work downstream."""
    frame = next(iter(iter_frames(sample_video, fps=1.0)))

    frame.image[0, 0] = 0  # must not raise


def test_stopping_early_does_not_raise(sample_video):
    """Taking only the first frames is legitimate, not an ffmpeg failure."""
    for count, _ in enumerate(iter_frames(sample_video, fps=10.0), start=1):
        if count == 2:
            break
