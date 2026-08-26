"""Command line surface.

Deliberately thin: every command is a call into `pipeline` plus output
formatting. Anything a command can do must also be reachable from
Python, so nothing worth testing lives here.

Stage 1 prints plain text. The interactive session, the banner, and the
theme arrive in Stage 5 and replace only the rendering, not the flow.

Data goes to stdout and human-facing messages go to stderr, so the
output can be piped.
"""

from __future__ import annotations

import json as jsonlib
import sys
from pathlib import Path

import typer

from amonhen import __version__
from amonhen.model_registry import DEFAULT_MODEL, get_model
from amonhen.pipeline import IndexConfig, index_videos
from amonhen.pipeline import search as run_search
from amonhen.progress import NullReporter
from amonhen.store import IncompatibleIndexError, Store

app = typer.Typer(
    add_completion=False,
    help="Search your videos by describing what you are looking for. Runs locally on CPU.",
)

DEFAULT_DB = Path.home() / ".amonhen" / "index.db"


def _build_image_encoder(model_id: str):
    from amonhen.encode import ImageEncoder

    return ImageEncoder(get_model(model_id))


def _build_text_encoder(model_id: str):
    from amonhen.encode import TextEncoder

    return TextEncoder(get_model(model_id))


def _embed_dim_for(model_id: str) -> int:
    return get_model(model_id).embed_dim


def _open_store(db: Path, model_id: str) -> Store:
    try:
        return Store(db, embed_dim=_embed_dim_for(model_id))
    except IncompatibleIndexError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error


def _format_timestamp(ts_ms: int) -> str:
    total_seconds, milliseconds = divmod(int(ts_ms), 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds // 100}"


@app.callback(invoke_without_command=True)
def default_entry(
    ctx: typer.Context,
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
) -> None:
    """Amon Hen CLI and Interactive Session."""
    if ctx.invoked_subcommand is None:
        from amonhen.interactive import run_interactive_session

        store = _open_store(db, model)
        try:
            run_interactive_session(store, _build_text_encoder(model), model_id=model)
        finally:
            store.close()


@app.command()
def index(
    paths: list[str] = typer.Argument(..., help="Video files or directories to index."),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    fps: float = typer.Option(1.0, "--fps", help="Frames sampled per second of video."),
    sampler: str = typer.Option("fixed", "--sampler", help="Frame sampler: fixed or adaptive."),
    embed_dedup: float | None = typer.Option(
        None, "--embed-dedup", help="Drop frames whose embedding cosine similarity to the "
        "last kept frame exceeds this (0-1). Off by default."
    ),
    dedup_distance: int = typer.Option(
        4, "--dedup-distance", help="Adaptive sampler: drop a frame whose average hash "
        "is within this Hamming distance (0-64) of the last kept frame."
    ),
    blur_threshold: float | None = typer.Option(
        None, "--blur-threshold", help="Adaptive sampler: drop frames below this sharpness. "
        "Off by default; the right value depends on resolution and content."
    ),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    force: bool = typer.Option(False, "--force", help="Re-index even if unchanged."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """Index one or more videos into the local database."""
    for path in paths:
        if not Path(path).exists():
            typer.echo(f"not found: {path}", err=True)
            raise typer.Exit(code=1)

    store = _open_store(db, model)
    try:
        result = index_videos(
            paths,
            store,
            IndexConfig(
                fps=fps,
                sampler=sampler,
                model_id=model,
                embed_dedup_threshold=embed_dedup,
                dedup_hamming_threshold=dedup_distance,
                blur_sharpness_threshold=blur_threshold,
            ),
            _build_image_encoder(model),
            NullReporter(),
            force=force,
            text_encoder=_build_text_encoder(model),
        )
    finally:
        store.close()

    if json:
        typer.echo(
            jsonlib.dumps(
                {
                    "videos": result.videos,
                    "frames_decoded": result.frames_decoded,
                    "frames_kept": result.frames_kept,
                    "skipped": result.skipped,
                    "elapsed_s": round(result.elapsed_s, 3),
                }
            )
        )
        return

    typer.echo(
        f"Indexed {result.videos} video(s), {result.frames_kept} frames "
        f"in {result.elapsed_s:.1f}s"
    )
    for skipped in result.skipped:
        typer.echo(f"unchanged, skipped: {skipped}", err=True)


@app.command()
def search(
    query: str = typer.Argument(..., help="What to look for."),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    limit: int = typer.Option(10, "--limit", "-k", help="Maximum results."),
    merge_gap: float = typer.Option(
        4.0, "--merge-gap", help="Max time gap (seconds) between frames to merge into one segment."
    ),
    min_score: float | None = typer.Option(
        None, "--min-score", help="Minimum similarity score threshold (0.0-1.0)."
    ),
    calibrate: bool = typer.Option(
        True, "--calibrate/--no-calibrate", help="Use statistical score baseline calibration."
    ),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """Find moments matching a text description."""
    store = _open_store(db, model)
    try:
        segments = run_search(
            query,
            store,
            _build_text_encoder(model),
            limit=limit,
            max_gap_ms=int(merge_gap * 1000),
            min_score=min_score,
            calibrate=calibrate,
        )
    finally:
        store.close()

    if json:
        typer.echo(
            jsonlib.dumps(
                {
                    "query": query,
                    "results": [
                        {
                            "video": seg.video_path,
                            "start_ms": seg.start_ms,
                            "end_ms": seg.end_ms,
                            "best_ts_ms": seg.best_ts_ms,
                            "score": round(seg.score, 4),
                            "frame_count": seg.frame_count,
                        }
                        for seg in segments
                    ],
                }
            )
        )
        return

    if not segments:
        typer.echo("No results.", err=True)
        return

    for position, seg in enumerate(segments, start=1):
        name = Path(seg.video_path).name
        if seg.start_ms < seg.end_ms:
            time_str = f"{_format_timestamp(seg.start_ms)} - {_format_timestamp(seg.end_ms)}"
        else:
            time_str = f"{_format_timestamp(seg.start_ms):23}"
        typer.echo(f"{position:>2}. {time_str}  {seg.score:.3f}  {name}")


@app.command()
def videos(
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """List indexed videos."""
    store = _open_store(db, model)
    try:
        rows = store.list_videos()
    finally:
        store.close()

    if json:
        typer.echo(
            jsonlib.dumps(
                {
                    "videos": [
                        {
                            "path": row.path,
                            "duration_ms": row.duration_ms,
                            "frame_count": row.frame_count,
                            "model_id": row.model_id,
                        }
                        for row in rows
                    ]
                }
            )
        )
        return

    for row in rows:
        typer.echo(
            f"{_format_timestamp(row.duration_ms)}  {row.frame_count:>6} frames  {row.path}"
        )


@app.command()
def stats(
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """Show index totals."""
    store = _open_store(db, model)
    try:
        totals = store.stats()
    finally:
        store.close()

    if json:
        typer.echo(jsonlib.dumps(totals))
        return

    typer.echo(f"videos: {totals['videos']}")
    typer.echo(f"frames: {totals['frames']}")
    for reason, count in totals["by_reason"].items():
        typer.echo(f"  {reason}: {count}")


@app.command()
def setup(
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
) -> None:
    """Download the model files ahead of first use."""
    from amonhen.encode import ensure_model

    spec = get_model(model)
    typer.echo(f"Downloading {spec.repo_id} ...", err=True)
    location = ensure_model(spec)
    typer.echo(f"Model ready at {location}", err=True)


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


def main() -> None:
    sys.exit(app())
