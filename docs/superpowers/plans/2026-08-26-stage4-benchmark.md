# AmonHen Stage 4 (Benchmark & Evaluation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, reproducible benchmark harness to evaluate AmonHen on video moment retrieval accuracy (Recall@1, Recall@5, mIoU) and CPU system efficiency (speedup, query latency, storage footprint).

**Architecture:** Isolated in the `benchmarks/` package. `metrics.py` implements pure-Python mathematical metric functions; `dataset.py` parses ground truth annotations and provides synthetic video generation for fast offline tests; `run.py` executes benchmark sweeps across sampler configurations (Fixed, Adaptive, Adaptive+EmbedDedup) and formats the output into a GitHub-ready Markdown comparison table.

**Tech Stack:** Python 3.12+, NumPy, Typer, pytest, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-26-stage4-benchmark.md`

## Global Constraints

- Python 3.11 or newer.
- CPU only.
- `benchmarks/` is self-contained and not imported by `amonhen.*` core runtime.
- Unit tests run fast (<5s) with `uv run pytest`.
- Linter passes cleanly with `uv run ruff check .`.

---

### Task 1: Metric Calculation Engine (`benchmarks/metrics.py`)

**Files:**
- Create: `benchmarks/metrics.py`
- Test: `tests/test_benchmark_metrics.py`

**Interfaces:**
- Consumes: `amonhen.segment.Segment`.
- Produces:
  - `compute_iou(pred_start_s: float, pred_end_s: float, gt_start_s: float, gt_end_s: float) -> float`
  - `QueryResult` dataclass (`best_iou: float`, `r1_03: bool`, `r1_05: bool`, `r5_03: bool`, `r5_05: bool`, `latency_ms: float`)
  - `evaluate_query(segments: list[Segment], gt_start_s: float, gt_end_s: float, latency_ms: float = 0.0) -> QueryResult`
  - `BenchmarkReport` dataclass (`config_name: str`, `r1_03: float`, `r1_05: float`, `r5_03: float`, `miou: float`, `indexing_speedup: float`, `avg_latency_ms: float`, `storage_mb_per_hour: float`, `frames_kept_pct: float`)
  - `format_markdown_table(reports: list[BenchmarkReport]) -> str`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_benchmark_metrics.py`:

```python
from amonhen.segment import Segment
from benchmarks.metrics import (
    BenchmarkReport,
    compute_iou,
    evaluate_query,
    format_markdown_table,
)


def test_compute_iou_exact_match():
    assert compute_iou(10.0, 20.0, 10.0, 20.0) == 1.0


def test_compute_iou_disjoint():
    assert compute_iou(0.0, 5.0, 10.0, 15.0) == 0.0


def test_compute_iou_partial_overlap():
    # Intersection = [10, 15] (5s), Union = [5, 20] (15s) -> 5/15 = 1/3
    assert abs(compute_iou(5.0, 15.0, 10.0, 20.0) - (1.0 / 3.0)) < 1e-5


def test_evaluate_query_computes_recall_and_miou():
    seg1 = Segment(video_id=1, video_path="v.mp4", start_ms=10000, end_ms=20000, best_ts_ms=15000, score=0.9, frame_count=5)
    seg2 = Segment(video_id=1, video_path="v.mp4", start_ms=30000, end_ms=40000, best_ts_ms=35000, score=0.8, frame_count=5)

    # GT is 12s to 18s (inside seg1)
    res = evaluate_query([seg1, seg2], gt_start_s=12.0, gt_end_s=18.0, latency_ms=15.0)

    assert res.r1_03 is True
    assert res.r1_05 is True
    assert res.best_iou > 0.5
    assert res.latency_ms == 15.0


def test_format_markdown_table():
    reports = [
        BenchmarkReport(
            config_name="Fixed (1.0 fps)",
            r1_03=0.45,
            r1_05=0.30,
            r5_03=0.75,
            miou=0.35,
            indexing_speedup=8.5,
            avg_latency_ms=18.2,
            storage_mb_per_hour=12.4,
            frames_kept_pct=100.0,
        )
    ]
    table = format_markdown_table(reports)
    assert "Fixed (1.0 fps)" in table
    assert "8.5x RT" in table
    assert "18.2 ms" in table
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_benchmark_metrics.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'benchmarks'`)

- [ ] **Step 3: Write minimal implementation**

Create `benchmarks/__init__.py`:
```python
"""AmonHen benchmarking and evaluation harness."""
```

Create `benchmarks/metrics.py`:
```python
"""Evaluation metrics for Video Moment Retrieval and CPU indexing efficiency."""

from __future__ import annotations

from dataclasses import dataclass

from amonhen.segment import Segment


def compute_iou(
    pred_start_s: float,
    pred_end_s: float,
    gt_start_s: float,
    gt_end_s: float,
) -> float:
    intersection_start = max(pred_start_s, gt_start_s)
    intersection_end = min(pred_end_s, gt_end_s)
    intersection = max(0.0, intersection_end - intersection_start)

    union_start = min(pred_start_s, gt_start_s)
    union_end = max(pred_end_s, gt_end_s)
    union = max(0.0, union_end - union_start)

    if union <= 0.0:
        return 0.0
    return float(intersection / union)


@dataclass(frozen=True)
class QueryResult:
    best_iou: float
    r1_03: bool
    r1_05: bool
    r5_03: bool
    r5_05: bool
    latency_ms: float


def evaluate_query(
    segments: list[Segment],
    gt_start_s: float,
    gt_end_s: float,
    latency_ms: float = 0.0,
) -> QueryResult:
    if not segments:
        return QueryResult(
            best_iou=0.0,
            r1_03=False,
            r1_05=False,
            r5_03=False,
            r5_05=False,
            latency_ms=latency_ms,
        )

    # Top-1 segment
    top1 = segments[0]
    iou_top1 = compute_iou(
        top1.start_ms / 1000.0,
        top1.end_ms / 1000.0,
        gt_start_s,
        gt_end_s,
    )

    # Top-5 max IoU
    ious_top5 = [
        compute_iou(
            s.start_ms / 1000.0,
            s.end_ms / 1000.0,
            gt_start_s,
            gt_end_s,
        )
        for s in segments[:5]
    ]
    max_iou_top5 = max(ious_top5)

    return QueryResult(
        best_iou=iou_top1,
        r1_03=iou_top1 >= 0.3,
        r1_05=iou_top1 >= 0.5,
        r5_03=max_iou_top5 >= 0.3,
        r5_05=max_iou_top5 >= 0.5,
        latency_ms=latency_ms,
    )


@dataclass(frozen=True)
class BenchmarkReport:
    config_name: str
    r1_03: float
    r1_05: float
    r5_03: float
    miou: float
    indexing_speedup: float
    avg_latency_ms: float
    storage_mb_per_hour: float
    frames_kept_pct: float


def format_markdown_table(reports: list[BenchmarkReport]) -> str:
    lines = [
        "| Sampler Configuration | R@1 (IoU=0.3) | R@1 (IoU=0.5) | R@5 (IoU=0.3) | mIoU | Indexing Speed | Latency | Storage / Hour |",
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for r in reports:
        lines.append(
            f"| **{r.config_name}** | {r.r1_03:.3f} | {r.r1_05:.3f} | {r.r5_03:.3f} | "
            f"{r.miou:.3f} | {r.indexing_speedup:.1f}x RT | {r.avg_latency_ms:.1f} ms | "
            f"{r.storage_mb_per_hour:.1f} MB |"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_benchmark_metrics.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarks/__init__.py benchmarks/metrics.py tests/test_benchmark_metrics.py
git commit -m "feat: add benchmark metrics engine and markdown table formatter"
```

---

### Task 2: Dataset Loader & Synthetic Harness (`benchmarks/dataset.py`)

**Files:**
- Create: `benchmarks/dataset.py`
- Test: `tests/test_benchmark_dataset.py`

**Interfaces:**
- Consumes: file system, ffmpeg.
- Produces:
  - `AnnotationItem` dataclass (`query: str`, `start_s: float`, `end_s: float`).
  - `VideoDatasetItem` dataclass (`video_path: Path`, `duration_s: float`, `annotations: list[AnnotationItem]`).
  - `load_dataset(json_path: Path) -> list[VideoDatasetItem]`.
  - `generate_synthetic_benchmark(output_dir: Path, count: int = 2) -> list[VideoDatasetItem]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_benchmark_dataset.py`:

```python
import json
from pathlib import Path

from benchmarks.dataset import generate_synthetic_benchmark, load_dataset


def test_load_dataset_parses_json(tmp_path):
    video_file = tmp_path / "vid.mp4"
    video_file.write_bytes(b"dummy")
    annotation_data = [
        {
            "video_path": str(video_file),
            "duration_s": 20.0,
            "annotations": [
                {"query": "person jumping", "start_s": 5.0, "end_s": 10.0}
            ],
        }
    ]
    json_path = tmp_path / "annotations.json"
    json_path.write_text(json.dumps(annotation_data))

    dataset = load_dataset(json_path)
    assert len(dataset) == 1
    assert dataset[0].duration_s == 20.0
    assert len(dataset[0].annotations) == 1
    assert dataset[0].annotations[0].query == "person jumping"


def test_generate_synthetic_benchmark_creates_videos(tmp_path):
    dataset = generate_synthetic_benchmark(tmp_path / "synthetic", count=1)
    assert len(dataset) == 1
    assert dataset[0].video_path.exists()
    assert dataset[0].duration_s > 0
    assert len(dataset[0].annotations) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_benchmark_dataset.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'benchmarks.dataset'`)

- [ ] **Step 3: Write minimal implementation**

Create `benchmarks/dataset.py`:

```python
"""Benchmark dataset parsing and synthetic test dataset generator."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg


@dataclass(frozen=True)
class AnnotationItem:
    query: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class VideoDatasetItem:
    video_path: Path
    duration_s: float
    annotations: list[AnnotationItem]


def load_dataset(json_path: Path | str) -> list[VideoDatasetItem]:
    path = Path(json_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = []
    base_dir = path.parent
    for entry in raw:
        video_p = Path(entry["video_path"])
        if not video_p.is_absolute():
            video_p = (base_dir / video_p).resolve()
        annotations = [
            AnnotationItem(
                query=ann["query"],
                start_s=float(ann["start_s"]),
                end_s=float(ann["end_s"]),
            )
            for ann in entry.get("annotations", [])
        ]
        items.append(
            VideoDatasetItem(
                video_path=video_p,
                duration_s=float(entry["duration_s"]),
                annotations=annotations,
            )
        )
    return items


def generate_synthetic_benchmark(
    output_dir: Path | str, count: int = 2
) -> list[VideoDatasetItem]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    items: list[VideoDatasetItem] = []
    for i in range(count):
        video_path = out_dir / f"synth_{i:02d}.mp4"
        duration_s = 4.0
        subprocess.run(
            [
                ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc=size=64x64:rate=10:duration={duration_s}",
                "-pix_fmt",
                "yuv420p",
                str(video_path),
            ],
            check=True,
        )
        annotations = [
            AnnotationItem(
                query="a test pattern with color bars",
                start_s=0.5,
                end_s=3.5,
            )
        ]
        items.append(
            VideoDatasetItem(
                video_path=video_path,
                duration_s=duration_s,
                annotations=annotations,
            )
        )

    # Save accompanying annotations JSON
    manifest = [
        {
            "video_path": str(item.video_path.relative_to(out_dir)),
            "duration_s": item.duration_s,
            "annotations": [
                {
                    "query": a.query,
                    "start_s": a.start_s,
                    "end_s": a.end_s,
                }
                for a in item.annotations
            ],
        }
        for item in items
    ]
    (out_dir / "annotations.json").write_text(json.dumps(manifest, indent=2))
    return items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_benchmark_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add benchmarks/dataset.py tests/test_benchmark_dataset.py
git commit -m "feat: add benchmark dataset loader and synthetic video generator"
```

---

### Task 3: Benchmark Runner Engine & CLI (`benchmarks/run.py`)

**Files:**
- Create: `benchmarks/run.py`
- Test: `tests/test_benchmark_runner.py`

**Interfaces:**
- Consumes: `benchmarks.metrics`, `benchmarks.dataset`, `amonhen.pipeline`, `amonhen.store`, `amonhen.encode`.
- Produces:
  - `run_benchmark_sweep(dataset: list[VideoDatasetItem], scratch_dir: Path, text_encoder=None, image_encoder=None) -> list[BenchmarkReport]`.
  - CLI runner entrypoint via `typer`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_benchmark_runner.py`:

```python
import numpy as np

from benchmarks.dataset import generate_synthetic_benchmark
from benchmarks.run import run_benchmark_sweep


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_benchmark_runner.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'benchmarks.run'`)

- [ ] **Step 3: Write minimal implementation**

Create `benchmarks/run.py`:

```python
"""Main benchmark harness runner and CLI."""

from __future__ import annotations

import time
from pathlib import Path

import typer

from amonhen.model_registry import DEFAULT_MODEL, get_model
from amonhen.pipeline import IndexConfig, index_videos, search
from amonhen.progress import NullReporter
from amonhen.store import Store
from benchmarks.dataset import (
    VideoDatasetItem,
    generate_synthetic_benchmark,
    load_dataset,
)
from benchmarks.metrics import (
    BenchmarkReport,
    evaluate_query,
    format_markdown_table,
)

app = typer.Typer(add_completion=False, help="Run AmonHen evaluation benchmarks.")


def run_benchmark_sweep(
    dataset: list[VideoDatasetItem],
    scratch_dir: Path,
    text_encoder=None,
    image_encoder=None,
    model_id: str = DEFAULT_MODEL.model_id,
    embed_dim: int | None = None,
) -> list[BenchmarkReport]:
    scratch_dir.mkdir(parents=True, exist_ok=True)
    dim = embed_dim or get_model(model_id).embed_dim

    if text_encoder is None:
        from amonhen.encode import TextEncoder

        text_encoder = TextEncoder(get_model(model_id))
    if image_encoder is None:
        from amonhen.encode import ImageEncoder

        image_encoder = ImageEncoder(get_model(model_id))

    video_paths = [item.video_path for item in dataset]
    total_video_duration_s = sum(item.duration_s for item in dataset)

    configs = [
        ("Fixed (1.0 fps)", IndexConfig(fps=1.0, sampler="fixed", model_id=model_id)),
        ("Adaptive (Default)", IndexConfig(fps=1.0, sampler="adaptive", model_id=model_id)),
        (
            "Adaptive + Embed-Dedup",
            IndexConfig(fps=1.0, sampler="adaptive", embed_dedup_threshold=0.98, model_id=model_id),
        ),
    ]

    reports: list[BenchmarkReport] = []

    for name, config in configs:
        db_path = scratch_dir / f"bench_{config.sampler}_{config.embed_dedup_threshold}.db"
        if db_path.exists():
            db_path.unlink()

        store = Store(db_path, embed_dim=dim)
        index_res = index_videos(
            video_paths,
            store,
            config,
            image_encoder,
            reporter=NullReporter(),
            force=True,
            text_encoder=text_encoder,
        )

        indexing_speedup = (
            total_video_duration_s / max(index_res.elapsed_s, 1e-4)
            if index_res.elapsed_s > 0
            else 1.0
        )
        frames_kept_pct = (
            (index_res.frames_kept / max(index_res.frames_decoded, 1)) * 100.0
            if index_res.frames_decoded > 0
            else 100.0
        )
        db_size_mb = db_path.stat().st_size / (1024 * 1024)
        hours = max(total_video_duration_s / 3600.0, 1e-4)
        storage_mb_per_hour = db_size_mb / hours

        query_results = []
        for item in dataset:
            for ann in item.annotations:
                q_start = time.perf_counter()
                segments = search(
                    ann.query,
                    store,
                    text_encoder,
                    limit=5,
                    calibrate=False,
                )
                latency_ms = (time.perf_counter() - q_start) * 1000.0
                eval_res = evaluate_query(
                    segments,
                    gt_start_s=ann.start_s,
                    gt_end_s=ann.end_s,
                    latency_ms=latency_ms,
                )
                query_results.append(eval_res)

        store.close()
        if db_path.exists():
            db_path.unlink()

        total_q = len(query_results)
        if total_q > 0:
            r1_03 = sum(1 for q in query_results if q.r1_03) / total_q
            r1_05 = sum(1 for q in query_results if q.r1_05) / total_q
            r5_03 = sum(1 for q in query_results if q.r5_03) / total_q
            miou = sum(q.best_iou for q in query_results) / total_q
            avg_lat = sum(q.latency_ms for q in query_results) / total_q
        else:
            r1_03 = r1_05 = r5_03 = miou = avg_lat = 0.0

        reports.append(
            BenchmarkReport(
                config_name=name,
                r1_03=r1_03,
                r1_05=r1_05,
                r5_03=r5_03,
                miou=miou,
                indexing_speedup=indexing_speedup,
                avg_latency_ms=avg_lat,
                storage_mb_per_hour=storage_mb_per_hour,
                frames_kept_pct=frames_kept_pct,
            )
        )

    return reports


@app.command()
def main(
    data_dir: Path | None = typer.Option(None, "--data-dir", help="Path to annotations/videos dir."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Markdown output path."),
    samples: int = typer.Option(5, "--samples", help="Number of samples if synthetic."),
    synthetic: bool = typer.Option(False, "--synthetic", help="Run with generated synthetic dataset."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
) -> None:
    """Run benchmark comparison suite."""
    scratch = Path.home() / ".amonhen" / "benchmarks" / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)

    if synthetic or data_dir is None:
        typer.echo("Using synthetic benchmark dataset...", err=True)
        dataset_dir = scratch / "synthetic_data"
        dataset = generate_synthetic_benchmark(dataset_dir, count=samples)
    else:
        ann_file = data_dir / "annotations.json" if data_dir.is_dir() else data_dir
        dataset = load_dataset(ann_file)

    typer.echo(f"Loaded {len(dataset)} video(s) for benchmarking. Running configurations...", err=True)
    reports = run_benchmark_sweep(dataset, scratch_dir=scratch, model_id=model)

    markdown_table = format_markdown_table(reports)
    typer.echo("\n" + markdown_table)

    if output:
        output.write_text(markdown_table + "\n", encoding="utf-8")
        typer.echo(f"\nTable saved to {output}", err=True)


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_benchmark_runner.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite & linting**

Run: `uv run pytest`
Expected: all tests pass.
Run: `uv run ruff check .`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add benchmarks/run.py tests/test_benchmark_runner.py
git commit -m "feat: add benchmark runner engine and CLI command"
```
