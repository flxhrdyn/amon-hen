# AmonHen Stage 3 (Result Quality) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement segment merging and statistical score calibration to aggregate adjacent video frame hits into clean temporal segments and filter out non-matching queries.

**Architecture:** Candidate hits retrieved via oversampled KNN in `sqlite-vec` ($k = \max(\text{limit} \times 8, 32)$) are filtered by video baseline / manual thresholds, grouped by video, temporally sorted, and merged within a configurable time window (`max_gap_ms`). Lower-layer modules remain decoupled; segment merging is isolated in `amonhen.segment` and orchestrated in `amonhen.pipeline`.

**Tech Stack:** Python 3.12+, NumPy, SQLite + sqlite-vec, Typer, pytest, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-26-stage3-result-quality.md`

## Global Constraints

- Python 3.11 or newer.
- CPU only. No GPU dependencies.
- No network calls at query/search time.
- Only `amonhen.store` contains SQL statements.
- `amonhen.segment` does not import `pipeline`, `store`, `decode`, or `encode`.
- All tests must pass with `uv run pytest`.
- All code must pass `uv run ruff check .`.

---

### Task 1: Segment data model & temporal merging logic (`amonhen.segment`)

**Files:**
- Create: `src/amonhen/segment.py`
- Test: `tests/test_segment.py`

**Interfaces:**
- Consumes: `amonhen.store.Hit` (`video_id: int`, `video_path: str`, `ts_ms: int`, `score: float`).
- Produces:
  - `Segment` dataclass (`video_id: int`, `video_path: str`, `start_ms: int`, `end_ms: int`, `best_ts_ms: int`, `score: float`, `frame_count: int`).
  - `merge_hits(hits: list[Hit], max_gap_ms: int = 4000, limit: int = 10) -> list[Segment]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_segment.py`:

```python
from amonhen.segment import Segment, merge_hits
from amonhen.store import Hit


def test_merge_hits_empty_returns_empty():
    assert merge_hits([], max_gap_ms=4000, limit=10) == []


def test_merge_hits_single_hit_becomes_single_frame_segment():
    hit = Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.25)
    segments = merge_hits([hit], max_gap_ms=4000, limit=10)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.video_id == 1
    assert seg.video_path == "/path/a.mp4"
    assert seg.start_ms == 1000
    assert seg.end_ms == 1000
    assert seg.best_ts_ms == 1000
    assert seg.score == 0.25
    assert seg.frame_count == 1


def test_merge_hits_combines_adjacent_frames_in_same_video():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.20),
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=2000, score=0.30),
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=3500, score=0.25),
    ]
    segments = merge_hits(hits, max_gap_ms=2000, limit=10)

    assert len(segments) == 1
    seg = segments[0]
    assert seg.start_ms == 1000
    assert seg.end_ms == 3500
    assert seg.best_ts_ms == 2000
    assert seg.score == 0.30
    assert seg.frame_count == 3


def test_merge_hits_splits_when_gap_exceeds_threshold():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.20),
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=10000, score=0.35),
    ]
    segments = merge_hits(hits, max_gap_ms=4000, limit=10)

    assert len(segments) == 2
    # Highest score first
    assert segments[0].start_ms == 10000
    assert segments[0].score == 0.35
    assert segments[1].start_ms == 1000
    assert segments[1].score == 0.20


def test_merge_hits_isolates_different_videos():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=1000, score=0.25),
        Hit(video_id=2, video_path="/path/b.mp4", ts_ms=1200, score=0.30),
    ]
    segments = merge_hits(hits, max_gap_ms=4000, limit=10)

    assert len(segments) == 2
    assert segments[0].video_id == 2
    assert segments[1].video_id == 1


def test_merge_hits_respects_limit():
    hits = [
        Hit(video_id=1, video_path="/path/a.mp4", ts_ms=i * 10000, score=0.10 + i * 0.05)
        for i in range(10)
    ]
    segments = merge_hits(hits, max_gap_ms=2000, limit=3)
    assert len(segments) == 3
    assert segments[0].score > segments[1].score > segments[2].score
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_segment.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.segment'`

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/segment.py`:

```python
"""Temporal aggregation of raw frame hits into coherent segments.

Isolated from store and pipeline so that temporal merging rules can be
tested with pure data structures without touching database or model.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from amonhen.store import Hit


@dataclass(frozen=True)
class Segment:
    video_id: int
    video_path: str
    start_ms: int
    end_ms: int
    best_ts_ms: int
    score: float
    frame_count: int


def merge_hits(
    hits: list[Hit],
    max_gap_ms: int = 4000,
    limit: int = 10,
) -> list[Segment]:
    if not hits:
        return []

    # Group hits by video
    by_video: dict[int, list[Hit]] = defaultdict(list)
    for hit in hits:
        by_video[hit.video_id].append(hit)

    merged_segments: list[Segment] = []

    for video_id, video_hits in by_video.items():
        sorted_hits = sorted(video_hits, key=lambda h: h.ts_ms)
        path = sorted_hits[0].video_path

        current_start = sorted_hits[0].ts_ms
        current_end = sorted_hits[0].ts_ms
        current_best_ts = sorted_hits[0].ts_ms
        current_best_score = sorted_hits[0].score
        current_count = 1

        for hit in sorted_hits[1:]:
            if hit.ts_ms - current_end <= max_gap_ms:
                current_end = hit.ts_ms
                current_count += 1
                if hit.score > current_best_score:
                    current_best_score = hit.score
                    current_best_ts = hit.ts_ms
            else:
                merged_segments.append(
                    Segment(
                        video_id=video_id,
                        video_path=path,
                        start_ms=current_start,
                        end_ms=current_end,
                        best_ts_ms=current_best_ts,
                        score=current_best_score,
                        frame_count=current_count,
                    )
                )
                current_start = hit.ts_ms
                current_end = hit.ts_ms
                current_best_ts = hit.ts_ms
                current_best_score = hit.score
                current_count = 1

        merged_segments.append(
            Segment(
                video_id=video_id,
                video_path=path,
                start_ms=current_start,
                end_ms=current_end,
                best_ts_ms=current_best_ts,
                score=current_best_score,
                frame_count=current_count,
            )
        )

    merged_segments.sort(key=lambda s: s.score, reverse=True)
    return merged_segments[:limit]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_segment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/segment.py tests/test_segment.py
git commit -m "feat: add temporal segment merging logic"
```

---

### Task 2: Store baseline & embedding sampling support (`amonhen.store`)

**Files:**
- Modify: `src/amonhen/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: SQLite database connection.
- Produces:
  - `Store.set_score_baseline(video_id: int, baseline: float) -> None`
  - `Store.get_score_baselines() -> dict[int, float]`
  - `Store.sample_frame_embeddings(video_id: int, sample_size: int = 50) -> list[np.ndarray]`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_store.py`:

```python
def test_set_and_get_score_baselines(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("a.mp4", 1000, 10.0, 100, 1.0, "h1", "m1")
    v2 = store.add_video("b.mp4", 1000, 10.0, 100, 1.0, "h1", "m1")

    store.set_score_baseline(v1, 0.225)
    baselines = store.get_score_baselines()

    assert baselines.get(v1) == 0.225
    assert v2 not in baselines or baselines.get(v2) is None
    store.close()


def test_sample_frame_embeddings(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("a.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    records = [
        FrameRecord(ts_ms=i * 1000, embedding=np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32), kept_reason="fixed")
        for i in range(10)
    ]
    store.add_frames(v1, records)

    samples = store.sample_frame_embeddings(v1, sample_size=5)
    assert len(samples) == 5
    assert samples[0].shape == (4,)
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -k "score_baseline or sample_frame_embeddings" -v`
Expected: FAIL (`AttributeError: 'Store' object has no attribute 'set_score_baseline'`)

- [ ] **Step 3: Write minimal implementation**

In `src/amonhen/store.py`, add the methods:

```python
    def set_score_baseline(self, video_id: int, baseline: float) -> None:
        self._conn.execute(
            "UPDATE video SET score_baseline = ? WHERE id = ?",
            (baseline, video_id),
        )
        self._conn.commit()

    def get_score_baselines(self) -> dict[int, float]:
        rows = self._conn.execute(
            "SELECT id, score_baseline FROM video WHERE score_baseline IS NOT NULL"
        ).fetchall()
        return {int(row["id"]): float(row["score_baseline"]) for row in rows}

    def sample_frame_embeddings(self, video_id: int, sample_size: int = 50) -> list[np.ndarray]:
        rows = self._conn.execute(
            """
            SELECT v.embedding
            FROM vec_frame v
            JOIN frame f ON f.id = v.frame_id
            WHERE f.video_id = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (video_id, sample_size),
        ).fetchall()
        return [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/store.py tests/test_store.py
git commit -m "feat: add score baseline persist and embedding sampling to store"
```

---

### Task 3: Pipeline search & calibration integration (`amonhen.pipeline`)

**Files:**
- Modify: `src/amonhen/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `amonhen.store.Store`, `amonhen.segment.merge_hits`, `amonhen.segment.Segment`.
- Produces:
  - `compute_video_baseline(store: Store, video_id: int) -> float | None`
  - `search(query: str, store: Store, text_encoder, limit: int = 10, max_gap_ms: int = 4000, min_score: float | None = None, calibrate: bool = True) -> list[Segment]`

- [ ] **Step 1: Write the failing tests**

Update `tests/test_pipeline.py` to test baseline computation, oversampling, and segment retrieval:

```python
def test_search_returns_segments_with_merging(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    # Add frames with unit vectors
    f1 = FrameRecord(ts_ms=1000, embedding=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), kept_reason="fixed")
    f2 = FrameRecord(ts_ms=2000, embedding=np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32), kept_reason="fixed")
    store.add_frames(v1, [f1, f2])
    store.mark_complete(v1)

    class FakeTextEncoder:
        def embed(self, text: str):
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    segments = search("query", store, FakeTextEncoder(), limit=5, max_gap_ms=2000, calibrate=False)
    assert len(segments) == 1
    assert segments[0].start_ms == 1000
    assert segments[0].end_ms == 2000
    assert segments[0].frame_count == 2
    store.close()


def test_search_filters_below_min_score(tmp_path):
    store = Store(tmp_path / "index.db", embed_dim=4)
    v1 = store.add_video("sample.mp4", 10000, 10.0, 100, 1.0, "h1", "m1")
    f1 = FrameRecord(ts_ms=1000, embedding=np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32), kept_reason="fixed")
    store.add_frames(v1, [f1])
    store.mark_complete(v1)

    class FakeTextEncoder:
        def embed(self, text: str):
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    segments = search("query", store, FakeTextEncoder(), limit=5, min_score=0.9, calibrate=False)
    assert segments == []
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pipeline.py -k "test_search" -v`
Expected: FAIL / mismatch with Segment structure

- [ ] **Step 3: Write minimal implementation**

In `src/amonhen/pipeline.py`:
- Add baseline calibration helper:
```python
def compute_video_baseline(store: Store, video_id: int, sample_size: int = 50) -> float | None:
    embeddings = store.sample_frame_embeddings(video_id, sample_size=sample_size)
    if len(embeddings) < 5:
        return None
    matrix = np.stack(embeddings)
    sims = matrix @ matrix.T
    # Extract off-diagonal values
    n = sims.shape[0]
    off_diag = sims[~np.eye(n, dtype=bool)]
    if len(off_diag) == 0:
        return None
    mean = float(np.mean(off_diag))
    std = float(np.std(off_diag))
    return mean + 1.5 * std
```
- In `index_videos()`, compute and set baseline after `mark_complete(video_id)`:
```python
        baseline = compute_video_baseline(store, video_id)
        if baseline is not None:
            store.set_score_baseline(video_id, baseline)
```
- Update `search()`:
```python
from amonhen.segment import Segment, merge_hits

def search(
    query: str,
    store: Store,
    text_encoder,
    limit: int = 10,
    max_gap_ms: int = 4000,
    min_score: float | None = None,
    calibrate: bool = True,
) -> list[Segment]:
    vector = text_encoder.embed(query)
    candidate_k = max(limit * 8, 32)
    hits = store.search_vector(vector, limit=candidate_k)

    if not hits:
        return []

    baselines = store.get_score_baselines() if calibrate else {}

    filtered_hits = []
    for hit in hits:
        threshold = min_score
        if threshold is None and calibrate:
            threshold = baselines.get(hit.video_id)
        if threshold is not None and hit.score < threshold:
            continue
        filtered_hits.append(hit)

    return merge_hits(filtered_hits, max_gap_ms=max_gap_ms, limit=limit)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/pipeline.py tests/test_pipeline.py
git commit -m "feat: integrate segment merging and baseline calibration into search pipeline"
```

---

### Task 4: CLI update for segment search & output formatting (`amonhen.cli`)

**Files:**
- Modify: `src/amonhen/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `amonhen.pipeline.search` returning `list[Segment]`.
- Produces:
  - Updated CLI command `amon-hen search` with `--merge-gap`, `--min-score`, `--no-calibrate`.
  - Human-formatted range display: `00:01:05.0 - 00:01:08.0` or single timestamp.
  - JSON output schema with `start_ms`, `end_ms`, `best_ts_ms`, `score`, `frame_count`.

- [ ] **Step 1: Write the failing tests**

Update `tests/test_cli.py` to assert segment output formatting in human text and JSON modes:

```python
def test_search_cli_displays_segment_range(runner, sample_db):
    result = runner.invoke(app, ["search", "test", "--db", str(sample_db)])
    assert result.exit_code == 0


def test_search_cli_json_outputs_segment_fields(runner, sample_db):
    result = runner.invoke(app, ["search", "test", "--db", str(sample_db), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "results" in data
    if data["results"]:
        first = data["results"][0]
        assert "start_ms" in first
        assert "end_ms" in first
        assert "best_ts_ms" in first
        assert "frame_count" in first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -k "test_search" -v`
Expected: FAIL (argument or output schema differences)

- [ ] **Step 3: Write minimal implementation**

In `src/amonhen/cli.py`, update `search`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite & linting**

Run: `uv run pytest`
Expected: all tests pass.
Run: `uv run ruff check .`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add src/amonhen/cli.py tests/test_cli.py
git commit -m "feat: support segment search options and range formatting in CLI"
```

---

## Execution Choice

Plan complete and ready to execute. Two execution options:
1. **Subagent-Driven (recommended)** - Fresh subagent per task with review checkpoints.
2. **Inline Execution** - Sequential execution within this session with checkpoints.
