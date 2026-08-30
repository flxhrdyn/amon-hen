from unittest.mock import MagicMock, patch

from amonhen.interactive import (
    format_segment_results,
    handle_slash_command,
    run_interactive_session,
)
from amonhen.segment import Segment


def test_handle_slash_command_help():
    out, should_exit = handle_slash_command("/help", last_results=[], store=None)
    assert "Available commands" in out
    assert should_exit is False


def test_handle_slash_command_exit():
    out, should_exit = handle_slash_command("/exit", last_results=[], store=None)
    assert "Farewell" in out
    assert should_exit is True

    out, should_exit = handle_slash_command("/quit", last_results=[], store=None)
    assert "Farewell" in out
    assert should_exit is True


def test_handle_slash_command_open():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=1000,
        end_ms=2000,
        best_ts_ms=1500,
        score=0.8,
        frame_count=1,
    )
    with patch("amonhen.interactive.open_video_at", return_value=True) as mock_open:
        out, should_exit = handle_slash_command("/open 1", last_results=[seg], store=None)
        assert "Opening" in out
        assert should_exit is False
        mock_open.assert_called_once_with("v.mp4", 1500)


def test_handle_slash_command_shorthand_open():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=1000,
        end_ms=2000,
        best_ts_ms=1500,
        score=0.8,
        frame_count=1,
    )
    with patch("amonhen.interactive.open_video_at", return_value=True) as mock_open:
        out, should_exit = handle_slash_command("/1", last_results=[seg], store=None)
        assert "Opening" in out
        assert should_exit is False
        mock_open.assert_called_once_with("v.mp4", 1500)


def test_handle_slash_command_open_out_of_bounds():
    out, should_exit = handle_slash_command("/open 5", last_results=[], store=None)
    assert "not found" in out
    assert should_exit is False


def test_handle_slash_command_open_player_failure():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=1000,
        end_ms=2000,
        best_ts_ms=1500,
        score=0.8,
        frame_count=1,
    )
    with patch("amonhen.interactive.open_video_at", return_value=False):
        out, should_exit = handle_slash_command("/open 1", last_results=[seg], store=None)
        assert "Could not launch media player" in out
        assert should_exit is False


def test_handle_slash_command_videos():
    mock_store = MagicMock()
    mock_video = MagicMock()
    mock_video.path = "video1.mp4"
    mock_video.duration_ms = 120000
    mock_video.frame_count = 120
    mock_store.list_videos.return_value = [mock_video]

    out, should_exit = handle_slash_command("/videos", last_results=[], store=mock_store)
    assert "video1.mp4" in out
    assert "120s" in out
    assert should_exit is False


def test_handle_slash_command_videos_empty():
    mock_store = MagicMock()
    mock_store.list_videos.return_value = []

    out, should_exit = handle_slash_command("/videos", last_results=[], store=mock_store)
    assert "No videos indexed yet" in out
    assert should_exit is False


def test_handle_slash_command_stats():
    mock_store = MagicMock()
    mock_store.stats.return_value = {"videos": 2, "frames": 100}

    out, should_exit = handle_slash_command("/stats", last_results=[], store=mock_store)
    assert "Videos: 2" in out
    assert "Frames: 100" in out
    assert should_exit is False


def test_handle_slash_command_cut_valid_index():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=1000,
        end_ms=4000,
        best_ts_ms=2500,
        score=0.8,
        frame_count=3,
    )
    with patch(
        "amonhen.interactive.cut_video_segment", return_value="v_clip_00m01s_00m04s.mp4"
    ) as mock_cut:
        out, should_exit = handle_slash_command("/cut 1", last_results=[seg], store=None)
        assert "Exported clip #1" in out
        assert "v_clip_00m01s_00m04s.mp4" in out
        assert should_exit is False
        mock_cut.assert_called_once_with(
            video_path="v.mp4",
            start_ms=1000,
            end_ms=4000,
            out_path=None,
        )


def test_handle_slash_command_cut_single_frame_applies_padding():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=5000,
        end_ms=5000,
        best_ts_ms=5000,
        score=0.8,
        frame_count=1,
    )
    with patch(
        "amonhen.interactive.cut_video_segment", return_value="v_clip_padded.mp4"
    ) as mock_cut:
        out, should_exit = handle_slash_command("/cut 1", last_results=[seg], store=None)
        assert "Exported clip #1" in out
        assert should_exit is False
        # start 5000 - 2000 = 3000, end 5000 + 2000 = 7000
        mock_cut.assert_called_once_with(
            video_path="v.mp4",
            start_ms=3000,
            end_ms=7000,
            out_path=None,
        )


def test_handle_slash_command_cut_custom_name():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=1000,
        end_ms=4000,
        best_ts_ms=2500,
        score=0.8,
        frame_count=3,
    )
    with patch("amonhen.interactive.cut_video_segment", return_value="custom_clip.mp4") as mock_cut:
        out, should_exit = handle_slash_command(
            "/cut 1 custom_clip.mp4", last_results=[seg], store=None
        )
        assert "Exported clip #1" in out
        assert "custom_clip.mp4" in out
        assert should_exit is False
        mock_cut.assert_called_once_with(
            video_path="v.mp4",
            start_ms=1000,
            end_ms=4000,
            out_path="custom_clip.mp4",
        )


def test_handle_slash_command_cut_out_of_bounds():
    out, should_exit = handle_slash_command("/cut 5", last_results=[], store=None)
    assert "not found" in out
    assert should_exit is False


def test_handle_slash_command_cut_failure():
    seg = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=1000,
        end_ms=4000,
        best_ts_ms=2500,
        score=0.8,
        frame_count=3,
    )
    with patch(
        "amonhen.interactive.cut_video_segment",
        side_effect=RuntimeError("FFmpeg error"),
    ):
        out, should_exit = handle_slash_command("/cut 1", last_results=[seg], store=None)
        assert "Could not export clip" in out
        assert should_exit is False


def test_handle_slash_command_unknown():
    out, should_exit = handle_slash_command("/foo", last_results=[], store=None)
    assert "Unknown command" in out
    assert should_exit is False


def test_format_segment_results():
    seg1 = Segment(
        video_id=1,
        video_path="/path/to/test.mp4",
        start_ms=1000,
        end_ms=5000,
        best_ts_ms=3000,
        score=0.85,
        frame_count=4,
    )
    seg2 = Segment(
        video_id=1,
        video_path="/path/to/test.mp4",
        start_ms=7000,
        end_ms=7000,
        best_ts_ms=7000,
        score=0.45,
        frame_count=1,
    )

    formatted = format_segment_results([seg1, seg2])
    assert "test.mp4" in formatted
    assert "0.850" in formatted
    assert "0.450" in formatted


def test_format_segment_results_empty():
    formatted = format_segment_results([])
    assert "No matching moments found." in formatted


def test_run_interactive_session_lifecycle(capsys):
    mock_store = MagicMock()
    mock_store.list_videos.return_value = []
    mock_encoder = MagicMock()

    inputs = ["find cats", "/exit"]
    mock_session = MagicMock()
    mock_session.prompt.side_effect = inputs

    with patch("amonhen.interactive.PromptSession", return_value=mock_session):
        with patch("amonhen.pipeline.search", return_value=[]) as mock_search:
            run_interactive_session(mock_store, mock_encoder)
            mock_search.assert_called_once_with("find cats", mock_store, mock_encoder, limit=5)

    captured = capsys.readouterr()
    assert "Amon Hen" in captured.out
    assert "Farewell" in captured.out


def test_run_interactive_session_eof(capsys):
    mock_store = MagicMock()
    mock_store.list_videos.return_value = []
    mock_encoder = MagicMock()

    mock_session = MagicMock()
    mock_session.prompt.side_effect = EOFError

    with patch("amonhen.interactive.PromptSession", return_value=mock_session):
        run_interactive_session(mock_store, mock_encoder)

    captured = capsys.readouterr()
    assert "Farewell" in captured.out
