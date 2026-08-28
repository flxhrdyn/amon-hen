import re
from unittest.mock import patch

import numpy as np
from benchmarks.dataset import generate_synthetic_benchmark
from benchmarks.metrics import BenchmarkReport
from benchmarks.run import app, run_benchmark_sweep
from typer.testing import CliRunner

runner = CliRunner()


class FakeTextEncoder:
    def embed(self, text: str):
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)


class FakeImageEncoder:
    def embed(self, images):
        n = len(images)
        return np.tile(np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), (n, 1))


def test_run_benchmark_sweep_executes_and_generates_reports(tmp_path):
    dataset = generate_synthetic_benchmark(tmp_path / "data", count=1)
    reports = run_benchmark_sweep(
        dataset,
        scratch_dir=tmp_path / "scratch",
        text_encoder=FakeTextEncoder(),
        image_encoder=FakeImageEncoder(),
        embed_dim=4,
    )
    assert len(reports) == 3
    assert reports[0].config_name.startswith("Fixed")
    assert reports[1].config_name.startswith("Adaptive")
    assert reports[2].config_name.startswith("Adaptive + Embed-Dedup")


def test_cli_help():
    result = runner.invoke(app, ["--help"], color=False)
    clean_output = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", result.output)
    assert result.exit_code == 0
    assert "Run benchmark comparison suite." in clean_output
    assert "--data-dir" in clean_output
    assert "--synthetic" in clean_output


def test_cli_synthetic_run_with_output(tmp_path):
    fake_report = [
        BenchmarkReport(
            config_name="Fixed (1.0 fps)",
            r1_03=0.5,
            r1_05=0.3,
            r5_03=0.8,
            miou=0.4,
            indexing_speedup=10.0,
            avg_latency_ms=15.0,
            storage_mb_per_hour=5.0,
            frames_kept_pct=100.0,
        )
    ]
    out_file = tmp_path / "result.md"
    with patch("benchmarks.run.run_benchmark_sweep", return_value=fake_report):
        result = runner.invoke(
            app,
            ["--synthetic", "--samples", "1", "-o", str(out_file)],
        )
        assert result.exit_code == 0
        assert out_file.exists()
        assert "Fixed (1.0 fps)" in out_file.read_text(encoding="utf-8")
