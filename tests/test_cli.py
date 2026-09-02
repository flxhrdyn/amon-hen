import json

import numpy as np
import pytest
from typer.testing import CliRunner

from amonhen.cli import app

DIM = 8
runner = CliRunner()


class StubEncoder:
    embed_dim = DIM

    def embed(self, images):
        if not images:
            return np.zeros((0, DIM), dtype=np.float32)
        out = np.zeros((len(images), DIM), dtype=np.float32)
        for row, image in enumerate(images):
            out[row, int(image.mean()) % DIM] = 1.0
        return out


class StubTextEncoder:
    embed_dim = DIM

    def embed(self, text: str) -> np.ndarray:
        vector = np.zeros(DIM, dtype=np.float32)
        vector[0] = 1.0
        return vector


@pytest.fixture(autouse=True)
def stub_encoders(monkeypatch):
    """Replace the real encoders so CLI tests never download a model."""
    import amonhen.cli as cli

    monkeypatch.setattr(cli, "_build_image_encoder", lambda model_id: StubEncoder())
    monkeypatch.setattr(cli, "_build_text_encoder", lambda model_id: StubTextEncoder())
    monkeypatch.setattr(cli, "_embed_dim_for", lambda model_id: DIM)


def test_index_then_search_reports_a_hit(tmp_path, sample_video):
    db = tmp_path / "index.db"

    indexed = runner.invoke(app, ["index", sample_video, "--db", str(db)])
    assert indexed.exit_code == 0

    found = runner.invoke(app, ["search", "anything", "--db", str(db)])
    assert found.exit_code == 0
    assert "sample.mp4" in found.stdout


def test_search_json_output_is_parseable_and_undecorated(tmp_path, sample_video):
    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db), "--json"])

    result = runner.invoke(app, ["search", "anything", "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert isinstance(payload["results"], list)
    assert len(payload["results"]) > 0
    assert {
        "video",
        "start_ms",
        "end_ms",
        "best_ts_ms",
        "score",
        "frame_count",
    } <= set(payload["results"][0])
    assert "\x1b[" not in result.stdout


def test_search_cli_displays_single_frame_and_range_formatting(tmp_path, sample_video, monkeypatch):
    import amonhen.cli as cli
    from amonhen.segment import Segment

    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    # Stub run_search to return both a range segment and a single-frame segment
    fake_segments = [
        Segment(
            video_id=1,
            video_path="/path/to/range_video.mp4",
            start_ms=65000,
            end_ms=68000,
            best_ts_ms=66000,
            score=0.2702,
            frame_count=4,
        ),
        Segment(
            video_id=1,
            video_path="/path/to/single_video.mp4",
            start_ms=6000,
            end_ms=6000,
            best_ts_ms=6000,
            score=0.2631,
            frame_count=1,
        ),
    ]
    monkeypatch.setattr(cli, "run_search", lambda *args, **kwargs: fake_segments)

    result = runner.invoke(app, ["search", "test", "--db", str(db)])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    # Range segment: 00:01:05.0 - 00:01:08.0
    assert "00:01:05.0 - 00:01:08.0" in lines[0]
    assert "range_video.mp4" in lines[0]
    assert "0.270" in lines[0]
    # Single-frame segment: 00:00:06.0 with padding to 23 chars
    assert "00:00:06.0             " in lines[1]
    assert "single_video.mp4" in lines[1]
    assert "0.263" in lines[1]


def test_search_cli_options_passed_to_run_search(tmp_path, sample_video, monkeypatch):
    import amonhen.cli as cli

    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    called_kwargs = {}

    def fake_run_search(query, store, text_encoder, **kwargs):
        called_kwargs.update(kwargs)
        return []

    monkeypatch.setattr(cli, "run_search", fake_run_search)

    result = runner.invoke(
        app,
        [
            "search",
            "test query",
            "--db",
            str(db),
            "--merge-gap",
            "2.5",
            "--min-score",
            "0.75",
            "--no-calibrate",
            "--limit",
            "5",
        ],
    )
    assert result.exit_code == 0
    assert called_kwargs["max_gap_ms"] == 2500
    assert called_kwargs["min_score"] == 0.75
    assert called_kwargs["calibrate"] is False
    assert called_kwargs["limit"] == 5


def test_search_cli_calibrate_flag(tmp_path, sample_video, monkeypatch):
    import amonhen.cli as cli

    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    called_kwargs = {}

    def fake_run_search(query, store, text_encoder, **kwargs):
        called_kwargs.update(kwargs)
        return []

    monkeypatch.setattr(cli, "run_search", fake_run_search)

    result = runner.invoke(
        app,
        ["search", "test query", "--db", str(db), "--calibrate"],
    )
    assert result.exit_code == 0
    assert called_kwargs["calibrate"] is True


def test_index_json_output_reports_counts(tmp_path, sample_video):
    db = tmp_path / "index.db"

    result = runner.invoke(app, ["index", sample_video, "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert payload["videos"] == 1
    assert payload["frames_kept"] > 0


def test_videos_lists_what_was_indexed(tmp_path, sample_video):
    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    result = runner.invoke(app, ["videos", "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert len(payload["videos"]) == 1
    assert payload["videos"][0]["frame_count"] > 0


def test_stats_reports_totals(tmp_path, sample_video):
    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    result = runner.invoke(app, ["stats", "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert payload["videos"] == 1
    assert payload["frames"] > 0


def test_search_on_an_empty_index_exits_cleanly(tmp_path):
    db = tmp_path / "empty.db"

    result = runner.invoke(app, ["search", "anything", "--db", str(db), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["results"] == []


def test_missing_video_file_fails_with_a_clear_message(tmp_path):
    result = runner.invoke(
        app, ["index", str(tmp_path / "nope.mp4"), "--db", str(tmp_path / "i.db")]
    )

    assert result.exit_code != 0


def test_cli_no_args_launches_interactive_session(tmp_path):
    from unittest.mock import MagicMock, patch

    db = tmp_path / "index.db"
    mock_run_session = MagicMock()

    with patch("amonhen.interactive.run_interactive_session", mock_run_session):
        result = runner.invoke(app, ["--db", str(db)])
        assert result.exit_code == 0
        assert mock_run_session.called


def test_cli_cut_command_text_output(tmp_path, sample_video):
    out_clip = tmp_path / "custom_out.mp4"
    result = runner.invoke(
        app,
        [
            "cut",
            sample_video,
            "--start",
            "00:01",
            "--end",
            "00:03",
            "-o",
            str(out_clip),
        ],
    )
    assert result.exit_code == 0
    assert "Exported clip" in result.stdout
    assert str(out_clip) in result.stdout
    assert out_clip.exists()


def test_cli_cut_command_json_output(tmp_path, sample_video):
    out_clip = tmp_path / "json_out.mp4"
    result = runner.invoke(
        app,
        [
            "cut",
            sample_video,
            "-s",
            "1.0",
            "-e",
            "2.5",
            "-o",
            str(out_clip),
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["start_ms"] == 1000
    assert payload["end_ms"] == 2500
    assert payload["clip_path"] == str(out_clip)
    assert payload["reencoded"] is False
    assert out_clip.exists()


def test_cli_cut_command_reencode_flag(tmp_path, sample_video):
    out_clip = tmp_path / "reencoded.mp4"
    result = runner.invoke(
        app,
        [
            "cut",
            sample_video,
            "--start",
            "0",
            "--end",
            "2",
            "-o",
            str(out_clip),
            "--reencode",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["reencoded"] is True
    assert out_clip.exists()


def test_cli_cut_command_invalid_timestamps_fails(sample_video):
    result = runner.invoke(
        app,
        ["cut", sample_video, "--start", "10", "--end", "5"],
    )
    assert result.exit_code != 0


def test_cli_search_speech_and_hybrid_modes(tmp_path, sample_video, monkeypatch):
    import amonhen.cli as cli
    from amonhen.segment import Segment

    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    # Mock run_search to return hybrid segment with spoken text
    def mock_run_search(*args, **kwargs):
        return [
            Segment(
                video_id=1,
                video_path="/path/to/sample.mp4",
                start_ms=1000,
                end_ms=5000,
                best_ts_ms=3000,
                score=0.85,
                frame_count=4,
                spoken_text="Hello world speech test",
                match_type=kwargs.get("mode", "hybrid"),
            )
        ]

    monkeypatch.setattr(cli, "run_search", mock_run_search)

    # Test human readable text with dialogue
    res = runner.invoke(app, ["search", "hello", "--db", str(db), "--mode", "hybrid"])
    assert res.exit_code == 0
    assert '💬 "Hello world speech test"' in res.stdout

    # Test JSON output
    res_json = runner.invoke(
        app, ["search", "hello", "--db", str(db), "--mode", "speech", "--json"]
    )
    assert res_json.exit_code == 0
    data = json.loads(res_json.stdout)
    assert data["results"][0]["spoken_text"] == "Hello world speech test"
    assert data["results"][0]["match_type"] == "speech"
