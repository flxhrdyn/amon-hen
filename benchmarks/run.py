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
    """Execute benchmark sweep across multiple sampler configurations."""
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
    data_dir: Path | None = typer.Option(
        None, "--data-dir", help="Path to annotations/videos dir."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Markdown output path."
    ),
    samples: int = typer.Option(5, "--samples", help="Number of samples if synthetic."),
    synthetic: bool = typer.Option(
        False, "--synthetic", help="Run with generated synthetic dataset."
    ),
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

    typer.echo(
        f"Loaded {len(dataset)} video(s) for benchmarking. Running configurations...",
        err=True,
    )
    reports = run_benchmark_sweep(dataset, scratch_dir=scratch, model_id=model)

    markdown_table = format_markdown_table(reports)
    typer.echo("\n" + markdown_table)

    if output:
        output.write_text(markdown_table + "\n", encoding="utf-8")
        typer.echo(f"\nTable saved to {output}", err=True)


if __name__ == "__main__":
    app()
