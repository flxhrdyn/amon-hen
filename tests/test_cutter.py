import pytest

from amonhen.cutter import (
    cut_video_segment,
    format_timestamp_tag,
    generate_clip_path,
    parse_timestamp,
)
from amonhen.decode import probe


def test_parse_timestamp_integers_and_floats():
    assert parse_timestamp(0) == 0
    assert parse_timestamp(10) == 10000
    assert parse_timestamp(12.5) == 12500
    assert parse_timestamp("45") == 45000
    assert parse_timestamp("75.25") == 75250


def test_parse_timestamp_mmss_and_hhmmss():
    assert parse_timestamp("00:10") == 10000
    assert parse_timestamp("01:15.5") == 75500
    assert parse_timestamp("00:01:15") == 75000
    assert parse_timestamp("01:02:03.4") == 3723400


def test_parse_timestamp_invalid_raises_value_error():
    with pytest.raises(ValueError, match="Invalid timestamp format"):
        parse_timestamp("invalid")
    with pytest.raises(ValueError, match="Invalid timestamp format"):
        parse_timestamp("12:34:56:78")
    with pytest.raises(ValueError, match="Timestamp cannot be negative"):
        parse_timestamp("-5")


def test_format_timestamp_tag():
    assert format_timestamp_tag(0) == "00m00s"
    assert format_timestamp_tag(75500) == "01m15s"
    assert format_timestamp_tag(3723000) == "01h02m03s"


def test_generate_clip_path_default_and_custom(tmp_path):
    video = tmp_path / "my_video.mp4"
    clip = generate_clip_path(video, start_ms=10000, end_ms=25000, out_dir=tmp_path)
    assert clip.name == "my_video_clip_00m10s_00m25s.mp4"
    assert clip.parent == tmp_path

    custom_clip = generate_clip_path(
        video, start_ms=10000, end_ms=25000, out_path=tmp_path / "custom.mp4"
    )
    assert custom_clip == tmp_path / "custom.mp4"


def test_cut_video_segment_stream_copy(sample_video, tmp_path):
    out_file = tmp_path / "cut_stream_copy.mp4"
    res = cut_video_segment(
        video_path=sample_video,
        start_ms=1000,
        end_ms=3000,
        out_path=out_file,
        reencode=False,
    )
    assert res.exists()
    assert res.stat().st_size > 0
    info = probe(res)
    assert 1000 <= info.duration_ms <= 4000


def test_cut_video_segment_reencode(sample_video, tmp_path):
    out_file = tmp_path / "cut_reencode.mp4"
    res = cut_video_segment(
        video_path=sample_video,
        start_ms=1000,
        end_ms=3000,
        out_path=out_file,
        reencode=True,
    )
    assert res.exists()
    assert res.stat().st_size > 0
    info = probe(res)
    assert 1800 <= info.duration_ms <= 2200


def test_cut_video_segment_invalid_bounds_raises_value_error(sample_video, tmp_path):
    with pytest.raises(ValueError, match="start_ms must be less than or equal to end_ms"):
        cut_video_segment(sample_video, start_ms=3000, end_ms=1000, out_path=tmp_path / "err.mp4")


def test_cut_video_segment_nonexistent_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        cut_video_segment(tmp_path / "ghost.mp4", start_ms=0, end_ms=1000)
