# AmonHen Stage 5 (Interactive Interface & Tolkien Theme) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full interactive REPL session, media player launching at specific timestamps, dual-level Rich progress bar, Tolkien-themed formatting, and slash command handling.

**Architecture:** `player.py` detects media players and executes seeking commands; `theme.py` defines ASCII banner, color palettes, and turning verbs; `progress.py` gains `RichReporter`; `interactive.py` uses `prompt_toolkit` to handle the interactive loop, history persistence, and slash commands; `cli.py` invokes the interactive session when run without arguments.

**Tech Stack:** Python 3.12+, Rich, prompt_toolkit, Typer, pytest, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-26-stage5-interactive-ui.md`

## Global Constraints

- Python 3.11 or newer.
- CPU only.
- When `--plain`, `NO_COLOR`, or non-TTY is detected, banners and color codes are cleanly omitted.
- Unit tests run fast (<5s) with `uv run pytest`.
- Linter passes cleanly with `uv run ruff check .`.

---

### Task 1: Media Player Launcher (`amonhen.player`)

**Files:**
- Create: `src/amonhen/player.py`
- Test: `tests/test_player.py`

**Interfaces:**
- Produces:
  - `build_player_command(video_path: Path | str, ts_ms: int, player_binary: str | None = None) -> list[str]`
  - `open_video_at(video_path: Path | str, ts_ms: int, player_command: str | None = None) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_player.py`:

```python
from amonhen.player import build_player_command, open_video_at


def test_build_player_command_mpv():
    cmd = build_player_command("video.mp4", 12500, player_binary="mpv")
    assert cmd == ["mpv", "--start=12.5", "video.mp4"]


def test_build_player_command_vlc():
    cmd = build_player_command("video.mp4", 12500, player_binary="vlc")
    assert cmd == ["vlc", "--start-time=12.5", "video.mp4"]


def test_build_player_command_ffplay():
    cmd = build_player_command("video.mp4", 12500, player_binary="ffplay")
    assert cmd == ["ffplay", "-ss", "12.5", "-autoexit", "video.mp4"]


def test_open_video_at_nonexistent_returns_false():
    assert open_video_at("nonexistent_file_path_12345.mp4", 1000) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_player.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'amonhen.player'`)

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/player.py`:

```python
"""Launch media players at specific timestamps with OS fallback."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path


def build_player_command(
    video_path: Path | str,
    ts_ms: int,
    player_binary: str | None = None,
) -> list[str]:
    path_str = str(video_path)
    ts_s = f"{ts_ms / 1000.0:.1f}"

    binary = player_binary
    if binary is None:
        for candidate in ("mpv", "vlc", "ffplay"):
            if shutil.which(candidate):
                binary = candidate
                break

    if binary == "mpv":
        return ["mpv", f"--start={ts_s}", path_str]
    if binary == "vlc":
        return ["vlc", f"--start-time={ts_s}", path_str]
    if binary == "ffplay":
        return ["ffplay", "-ss", ts_s, "-autoexit", path_str]

    return [path_str]


def open_video_at(
    video_path: Path | str,
    ts_ms: int,
    player_command: str | None = None,
) -> bool:
    path = Path(video_path)
    if not path.exists():
        return False

    cmd = build_player_command(path, ts_ms, player_binary=player_command)
    try:
        if len(cmd) > 1:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        # OS Default fallback
        if platform.system() == "Windows":
            os.startfile(str(path))
            return True
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(path)])
            return True
        else:
            subprocess.Popen(["xdg-open", str(path)])
            return True
    except Exception:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_player.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/player.py tests/test_player.py
git commit -m "feat: add media player launcher with timestamp seeking"
```

---

### Task 2: Theme, ASCII Banner, & Turning Verbs (`amonhen.theme`)

**Files:**
- Create: `src/amonhen/theme.py`
- Test: `tests/test_theme.py`

**Interfaces:**
- Produces:
  - `render_banner(model_id: str = "mobileclip2-s2", videos_count: int = 0, plain: bool = False) -> str`
  - `format_score_bar(score: float, width: int = 10) -> str`
  - `get_turning_verb(seed: int | None = None) -> str`
  - `is_color_disabled() -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_theme.py`:

```python
from amonhen.theme import format_score_bar, get_turning_verb, is_color_disabled, render_banner


def test_render_banner_contains_title_and_tagline():
    banner = render_banner(model_id="mobileclip2-s2", videos_count=5, plain=False)
    assert "Amon Hen" in banner
    assert "Seat of Seeing" in banner
    assert "mobileclip2-s2" in banner


def test_render_banner_plain_mode():
    banner = render_banner(model_id="mobileclip2-s2", videos_count=5, plain=True)
    assert "Amon Hen" in banner
    assert "\033[" not in banner  # No ANSI escapes in plain mode


def test_format_score_bar():
    bar = format_score_bar(0.5, width=10)
    assert len(bar) == 10
    assert "█" in bar
    assert "░" in bar


def test_get_turning_verb():
    verb = get_turning_verb(seed=42)
    assert isinstance(verb, str)
    assert len(verb) > 0


def test_is_color_disabled_respects_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert is_color_disabled() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_theme.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'amonhen.theme'`)

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/theme.py`:

```python
"""Theme styling, Tolkien aesthetics, turning verbs, and banner rendering."""

from __future__ import annotations

import os
import sys

from amonhen import __version__

TURNING_VERBS = (
    "gazing",
    "surveying",
    "discerning",
    "seeking",
    "scouring",
    "unveiling",
    "delving",
    "glimpsing",
    "perceiving",
    "watching",
)


def is_color_disabled() -> bool:
    return bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()


def get_turning_verb(seed: int | None = None) -> str:
    if seed is not None:
        return TURNING_VERBS[seed % len(TURNING_VERBS)]
    import random

    return random.choice(TURNING_VERBS)


def format_score_bar(score: float, width: int = 10) -> str:
    clamped = max(0.0, min(1.0, score))
    filled = int(round(clamped * width))
    return "█" * filled + "░" * (width - filled)


def render_banner(
    model_id: str = "mobileclip2-s2",
    videos_count: int = 0,
    plain: bool = False,
) -> str:
    use_plain = plain or is_color_disabled()
    title = "  A M O N   H E N  "
    tagline = '  "From the Seat of Seeing, no moment remains hidden."  '
    status = f"  v{__version__} | model: {model_id} | indexed: {videos_count} video(s)  "

    if use_plain:
        return f"\n{title}\n{tagline}\n{status}\n"

    # Subtle ANSI coloring: 33 = muted gold, 90 = stone gray, 36 = pale blue
    return (
        f"\n\033[1;33m{title}\033[0m\n"
        f"\033[3;90m{tagline}\033[0m\n"
        f"\033[36m{status}\033[0m\n"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_theme.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/theme.py tests/test_theme.py
git commit -m "feat: add Tolkien theme banner, turning verbs, and color styles"
```

---

### Task 3: Dual-Level Rich Progress Reporter (`amonhen.progress`)

**Files:**
- Modify: `src/amonhen/progress.py`
- Test: `tests/test_progress.py`

**Interfaces:**
- Produces:
  - `RichReporter(plain: bool = False)` implementing `Reporter` protocol with two progress bars and live status.

- [ ] **Step 1: Write the failing tests**

Update `tests/test_progress.py`:

```python
from amonhen.progress import NullReporter, RecordingReporter, RichReporter


def test_rich_reporter_handles_full_lifecycle():
    reporter = RichReporter(plain=True)
    reporter.video_started("test.mp4", total_ms=10000)
    reporter.frame_progress(decoded=10, stored=5, ts_ms=5000)
    reporter.video_finished("test.mp4", decoded=20, stored=10, elapsed_s=1.5)
    reporter.run_finished(videos=1, frames=10, elapsed_s=1.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_progress.py -k "test_rich_reporter" -v`
Expected: FAIL (`ImportError: cannot import name 'RichReporter'`)

- [ ] **Step 3: Write minimal implementation**

In `src/amonhen/progress.py`, implement `RichReporter`:

```python
class RichReporter:
    def __init__(self, plain: bool = False):
        self.plain = plain
        self._current_video = ""
        self._total_ms = 0

    def video_started(self, path: str, total_ms: int) -> None:
        self._current_video = Path(path).name
        self._total_ms = total_ms

    def frame_progress(self, decoded: int, stored: int, ts_ms: int) -> None:
        pass

    def video_finished(
        self, path: str, decoded: int, stored: int, elapsed_s: float
    ) -> None:
        pass

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_progress.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/progress.py tests/test_progress.py
git commit -m "feat: add Rich dual-level progress reporter"
```

---

### Task 4: Interactive REPL Session & CLI Routing (`amonhen.interactive` & `amonhen.cli`)

**Files:**
- Create: `src/amonhen/interactive.py`
- Modify: `src/amonhen/cli.py`
- Test: `tests/test_interactive.py`, `tests/test_cli.py`

**Interfaces:**
- Produces:
  - `InteractiveSession(store: Store, text_encoder, image_encoder)`
  - `run_interactive_session()`
  - CLI invocation without arguments starts interactive session.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_interactive.py`:

```python
from amonhen.interactive import handle_slash_command
from amonhen.segment import Segment


def test_handle_slash_command_help():
    out, should_exit = handle_slash_command("/help", last_results=[], store=None)
    assert "Available commands" in out
    assert should_exit is False


def test_handle_slash_command_exit():
    out, should_exit = handle_slash_command("/exit", last_results=[], store=None)
    assert should_exit is True


def test_handle_slash_command_open():
    seg = Segment(video_id=1, video_path="v.mp4", start_ms=1000, end_ms=2000, best_ts_ms=1500, score=0.8, frame_count=1)
    out, should_exit = handle_slash_command("/open 1", last_results=[seg], store=None)
    assert "Opening" in out or "not found" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_interactive.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'amonhen.interactive'`)

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/interactive.py`:

```python
"""Interactive REPL session for AmonHen."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from amonhen.player import open_video_at
from amonhen.segment import Segment
from amonhen.theme import format_score_bar, render_banner

if TYPE_CHECKING:
    from amonhen.store import Store

HISTORY_FILE = Path.home() / ".amonhen" / "history"


def format_segment_results(segments: list[Segment]) -> str:
    if not segments:
        return "No matching moments found."

    lines = []
    for i, seg in enumerate(segments, start=1):
        name = Path(seg.video_path).name
        start_s = seg.start_ms / 1000.0
        end_s = seg.end_ms / 1000.0
        if seg.start_ms < seg.end_ms:
            time_str = f"{int(start_s//60):02d}:{start_s%60:04.1f} - {int(end_s//60):02d}:{end_s%60:04.1f}"
        else:
            time_str = f"{int(start_s//60):02d}:{start_s%60:04.1f}              "
        bar = format_score_bar(seg.score, width=8)
        lines.append(f" {i:>2}. {time_str}  {bar} {seg.score:.3f}  {name}")
    return "\n".join(lines)


def handle_slash_command(
    cmd_line: str,
    last_results: list[Segment],
    store: Store | None,
) -> tuple[str, bool]:
    parts = cmd_line.strip().split()
    cmd = parts[0].lower()

    if cmd in ("/exit", "/quit"):
        return "Farewell.", True

    if cmd == "/help":
        help_text = (
            "Available commands:\n"
            "  <query text>      Search video moments by description\n"
            "  /open <number>    Open result in media player (e.g. /open 1 or /1)\n"
            "  /videos           List indexed videos\n"
            "  /stats            Show index statistics\n"
            "  /help             Show this help message\n"
            "  /exit             Exit interactive session"
        )
        return help_text, False

    if cmd.startswith("/") and cmd[1:].isdigit():
        idx = int(cmd[1:])
        return _open_index(idx, last_results)

    if cmd == "/open" and len(parts) > 1 and parts[1].isdigit():
        idx = int(parts[1])
        return _open_index(idx, last_results)

    if cmd == "/videos" and store:
        vids = store.list_videos()
        if not vids:
            return "No videos indexed yet.", False
        lines = [f"  {v.duration_ms // 1000}s  {v.frame_count} frames  {v.path}" for v in vids]
        return "\n".join(lines), False

    if cmd == "/stats" and store:
        st = store.stats()
        return f"Videos: {st['videos']} | Frames: {st['frames']}", False

    return f"Unknown command: {cmd_line}. Type /help for available commands.", False


def _open_index(idx: int, last_results: list[Segment]) -> tuple[str, bool]:
    if 1 <= idx <= len(last_results):
        seg = last_results[idx - 1]
        success = open_video_at(seg.video_path, seg.best_ts_ms)
        ts_s = seg.best_ts_ms / 1000.0
        time_str = f"{int(ts_s//60):02d}:{ts_s%60:04.1f}"
        if success:
            return f"Opening {Path(seg.video_path).name} at {time_str}...", False
        return f"Could not launch media player for {seg.video_path}", False
    return f"Result #{idx} not found. Last search returned {len(last_results)} result(s).", False


def run_interactive_session(
    store: Store,
    text_encoder,
    model_id: str = "mobileclip2-s2",
) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(HISTORY_FILE)))

    videos_count = len(store.list_videos())
    print(render_banner(model_id=model_id, videos_count=videos_count))
    print("Type your search query, /open <num> to launch video, or /help.\n")

    last_results: list[Segment] = []

    while True:
        try:
            line = session.prompt("amon-hen> ").strip()
            if not line:
                continue

            if line.startswith("/"):
                msg, should_exit = handle_slash_command(line, last_results, store)
                print(msg)
                if should_exit:
                    break
                continue

            # Natural search query
            from amonhen.pipeline import search

            last_results = search(line, store, text_encoder, limit=5)
            print(format_segment_results(last_results))
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nFarewell.")
            break
```

In `src/amonhen/cli.py`, add default interactive callback when no subcommand is provided:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_interactive.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite & linting**

Run: `uv run pytest`
Expected: all tests pass.
Run: `uv run ruff check .`
Expected: no lint errors.

- [ ] **Step 6: Commit**

```bash
git add src/amonhen/interactive.py src/amonhen/cli.py tests/test_interactive.py
git commit -m "feat: add interactive REPL session with history and slash commands"
```
