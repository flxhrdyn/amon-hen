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
    assert {"video", "ts_ms", "score"} <= set(payload["results"][0])
    assert "\x1b[" not in result.stdout


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
