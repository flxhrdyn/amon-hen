"""Interactive REPL session for AmonHen."""

from __future__ import annotations

import shlex
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit.history import FileHistory

from amonhen.cutter import cut_video_segment
from amonhen.player import open_video_at
from amonhen.segment import Segment
from amonhen.theme import (
    BLUE,
    BLUE_BOLD,
    MUTED,
    RESET,
    WHITE,
    format_score_bar,
    format_timestamp,
    get_turning_verb,
    render_banner,
)

if TYPE_CHECKING:
    from amonhen.store import Store


HISTORY_FILE = Path.home() / ".amonhen" / "history"


def _split_cmd(line: str) -> list[str]:
    try:
        return shlex.split(line.strip())
    except ValueError:
        # Unbalanced quotes: fall back to a plain split rather than raising.
        return line.strip().split()


class TuiReporter:
    """Reports indexing progress via a callback instead of writing to stdout,
    so a live bar can render inside the full-screen layout."""

    def __init__(self, on_progress) -> None:
        self._on_progress = on_progress
        self._name = ""
        self._total_ms = 0

    def video_started(self, path: str, total_ms: int) -> None:
        self._name = Path(path).name
        self._total_ms = total_ms
        self._on_progress(self._name, 0, self._total_ms)

    def frame_progress(self, decoded: int, stored: int, ts_ms: int) -> None:
        self._on_progress(self._name, ts_ms, self._total_ms)

    def video_finished(self, path: str, decoded: int, stored: int, elapsed_s: float) -> None:
        pass

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        pass


def format_segment_results(segments: list[Segment], width: int | None = None) -> str:
    if not segments:
        return "No matching moments found."

    if width is None:
        width = shutil.get_terminal_size(fallback=(100, 24)).columns
    blocks = []
    for i, seg in enumerate(segments, start=1):
        name = Path(seg.video_path).name
        t0 = format_timestamp(seg.start_ms)
        t1 = format_timestamp(seg.end_ms)
        time_str = f"{t0} -> {t1}" if seg.start_ms < seg.end_ms else f"{t0}              "
        peak_str = format_timestamp(seg.best_ts_ms)

        bar = format_score_bar(seg.score, width=10)
        bar_str = f"[{bar}] {seg.score:.3f}"
        highlight = i == 1

        if highlight:
            header = (
                f"{BLUE_BOLD}#{i}   {time_str:<23}{RESET}              {BLUE_BOLD}{bar_str}{RESET}"
            )
            meta = f"{MUTED}File: {name}   Peak: {peak_str}{RESET}"
            action = (
                f"{BLUE}=> Action: Type /open {i} to play moment (or /cut {i} to export){RESET}"
            )
            blocks.append(f"{header}\n{meta}\n{action}")
        else:
            header = f"{WHITE}#{i}   {time_str:<23}{RESET}              {BLUE}{bar_str}{RESET}"
            meta = f"{MUTED}File: {name}   Peak: {peak_str}{RESET}"
            blocks.append(f"{header}\n{meta}")

    return "\n\n".join(blocks)


def handle_slash_command(
    cmd_line: str,
    last_results: list[Segment],
    store: Store | None,
    model_id: str = "mobileclip2-s0",
) -> tuple[str, bool]:
    parts = _split_cmd(cmd_line)
    if not parts:
        return "", False
    cmd = parts[0].lower()

    if cmd in ("/exit", "/quit"):
        return "Farewell. The seeing closes.", True

    if cmd == "/help":
        help_text = (
            "Available commands:\n"
            "  <query text>            Search video moments by description\n"
            "  /index <dir_or_file>    Extract and index videos into database\n"
            "  /open <number>          Open result in media player (e.g. /open 1 or /1)\n"
            "  /cut <number> [output]  Export clip to video file (e.g. /cut 1)\n"
            "  /videos                 List indexed videos\n"
            "  /stats                  Show index statistics\n"
            "  /help                   Show this help message\n"
            "  /exit                   Exit interactive session"
        )
        return help_text, False

    if cmd.startswith("/") and cmd[1:].isdigit():
        idx = int(cmd[1:])
        return _open_index(idx, last_results)

    if cmd == "/open" and len(parts) > 1 and parts[1].isdigit():
        idx = int(parts[1])
        return _open_index(idx, last_results)

    if cmd == "/cut":
        if len(parts) < 2 or not parts[1].isdigit():
            return "Usage: /cut <result_number> [output_filename]", False
        idx = int(parts[1])
        out_name = parts[2] if len(parts) > 2 else None
        return _cut_index(idx, out_name, last_results)

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
        time_str = f"{int(ts_s // 60):02d}:{ts_s % 60:04.1f}"
        name = Path(seg.video_path).name
        if success:
            return f"{BLUE_BOLD}=> Launching media player at {time_str} ({name})...{RESET}", False
        return f"Could not launch media player for {seg.video_path}", False
    return f"Result #{idx} not found. Last search returned {len(last_results)} result(s).", False


def _cut_index(idx: int, out_name: str | None, last_results: list[Segment]) -> tuple[str, bool]:
    if 1 <= idx <= len(last_results):
        seg = last_results[idx - 1]
        start_ms = seg.start_ms
        end_ms = seg.end_ms
        if start_ms == end_ms:
            start_ms = max(0, start_ms - 2000)
            end_ms = end_ms + 2000

        try:
            clip_path = cut_video_segment(
                video_path=seg.video_path,
                start_ms=start_ms,
                end_ms=end_ms,
                out_path=out_name,
            )
            t0 = f"{int((start_ms / 1000) // 60):02d}:{(start_ms / 1000) % 60:04.1f}"
            t1 = f"{int((end_ms / 1000) // 60):02d}:{(end_ms / 1000) % 60:04.1f}"
            return (
                f"{BLUE_BOLD}=> Exported clip #{idx} ({t0} - {t1}) to:\n  {clip_path}{RESET}",
                False,
            )
        except Exception as e:
            return f"Could not export clip: {e}", False
    return f"Result #{idx} not found. Last search returned {len(last_results)} result(s).", False


def _footer_text(model_id: str, width: int) -> str:
    if width >= 80:
        left = "[Enter] Submit  ·  /index <dir>  ·  /open <id>  ·  /cut <id>  ·  /exit"
        right = f"{model_id.upper()} · CPU"
    elif width >= 60:
        left = "[Enter] Search  ·  /index  ·  /open  ·  /cut  ·  /exit"
        right = f"{model_id.upper()}"
    else:
        left = "[Enter] Search  ·  /help  ·  /exit"
        right = ""

    pad = " " * max(1, width - len(left) - len(right)) if right else ""
    return f"{MUTED}{left}{pad}{right}{RESET}"


def run_interactive_session(
    store: Store,
    text_encoder,
    model_id: str = "mobileclip2-s0",
    input=None,
    output=None,
) -> str:
    """Run the full-screen TUI. Returns the session's scrollback body (for tests)."""
    from prompt_toolkit.application import Application, get_app
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl

    # Any bare-stdout progress bar (huggingface_hub downloads, tqdm) would
    # tear straight through this full-screen layout, so silence them.
    try:
        from huggingface_hub.utils import disable_progress_bars

        disable_progress_bars()
    except ImportError:
        pass

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "last_results": [],
        "body": "",
        "progress": "",
        "busy": False,
        "videos_count": len(store.list_videos()),
        "total_frames": store.stats().get("frames", 0),
    }

    def header_text():
        width = get_app().output.get_size().columns
        return ANSI(
            render_banner(
                model_id=model_id,
                videos_count=state["videos_count"],
                total_frames=state["total_frames"],
                dir_path=str(store.path.parent),
                width=width,
                force_color=True,
            )
        )

    def body_text():
        if not state["body"] and not state["progress"]:
            return ANSI(
                f"{MUTED}Type a query in plain English to search your indexed videos.\n\n"
                f"  /index <path>   index new videos\n"
                f"  /open <id>      play a result\n"
                f"  /help           show all commands{RESET}"
            )
        return ANSI(state["body"] + state["progress"])

    def footer_text():
        width = get_app().output.get_size().columns
        return ANSI(_footer_text(model_id, width))

    def body_cursor_position():
        # FormattedTextControl has no real cursor, and with wrap_lines=True
        # prompt_toolkit *only* scrolls to keep this reported cursor line
        # visible (mouse wheel directly mutates Window.vertical_scroll on
        # Windows, bypassing key bindings entirely, but that mutation gets
        # discarded next render unless the cursor tracks it) - so mirror
        # whatever the window is currently scrolled to instead of pinning
        # to a fixed line, and let append()/scroll bindings drive
        # vertical_scroll directly. append() may set a large sentinel to
        # jump to the bottom before any render has clamped it, so clamp
        # here too or a stale huge index reaches the line-fragment lookup.
        line_count = (state["body"] + state["progress"]).count("\n")
        return Point(x=0, y=min(body_window.vertical_scroll, line_count))

    body_window = Window(
        FormattedTextControl(body_text, get_cursor_position=body_cursor_position),
        wrap_lines=True,
    )

    def append(text: str) -> None:
        state["body"] += text
        # New output jumps back to the bottom, like a terminal.
        body_window.vertical_scroll = 1_000_000

    # `get_app()` relies on a contextvar that isn't propagated into
    # run_in_executor's worker threads, where it silently returns a
    # no-op DummyApplication instead of raising - so background progress
    # callbacks must invalidate this captured reference directly.
    app_ref: list[Application] = []

    def invalidate() -> None:
        if app_ref:
            app_ref[0].invalidate()

    def run_query(line: str) -> None:
        from amonhen.pipeline import search

        t0 = time.perf_counter()
        results = search(line, store, text_encoder, limit=5)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        state["last_results"] = results

        verb = get_turning_verb().capitalize()
        # The real rendered pane width, not the raw OS console size - they
        # differ under VSCode's integrated terminal and similar hosts,
        # which wrapped this line onto a second row.
        width = get_app().output.get_size().columns
        right = f"{verb} in {elapsed_ms:.0f}ms"
        left = f"> {line}"
        pad = " " * max(1, width - len(left) - len(right))
        query_line = f"{BLUE_BOLD}>{RESET} {line}{pad}{MUTED}{right}{RESET}"
        append(f"\n{query_line}\n\n{format_segment_results(results, width=width)}\n\n")

    async def run_index_async(line: str) -> None:
        import asyncio

        from amonhen.encode import ImageEncoder
        from amonhen.model_registry import get_model
        from amonhen.pipeline import IndexConfig, index_videos

        append(f"\n{BLUE_BOLD}>{RESET} {line}\n")
        parts = _split_cmd(line)
        if len(parts) < 2:
            append("Usage: /index <path_to_video_or_dir>\n\n")
            return
        target_path = Path(parts[1])
        if not target_path.exists():
            append(f"Path does not exist: {target_path}\n\n")
            return

        def on_progress(name: str, ts_ms: int, total_ms: int) -> None:
            pct = min(1.0, ts_ms / total_ms) if total_ms else 0.0
            bar = format_score_bar(pct, width=30)
            state["progress"] = f"* Gazing {name}... [{BLUE}{bar}{RESET}]"
            invalidate()

        # Loading/downloading the model can take a while on first run, and
        # nothing calls on_progress until decoding actually starts, so show
        # something immediately instead of leaving the screen looking frozen.
        state["progress"] = f"{MUTED}* Preparing {model_id.upper()}...{RESET}"
        invalidate()

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: index_videos(
                    paths=[target_path],
                    store=store,
                    config=IndexConfig(model_id=model_id),
                    image_encoder=ImageEncoder(get_model(model_id)),
                    reporter=TuiReporter(on_progress),
                    text_encoder=text_encoder,
                ),
            )
            state["progress"] = ""
            state["videos_count"] = len(store.list_videos())
            state["total_frames"] = store.stats().get("frames", 0)
            append(
                f"{BLUE_BOLD}* Unveiled {result.videos} video(s) into database "
                f"(Index: {state['videos_count']} videos, {state['total_frames']} frames)."
                f"{RESET}\n\n"
            )
        except Exception as e:
            state["progress"] = ""
            append(f"Indexing failed: {e}\n\n")
        finally:
            state["busy"] = False
        invalidate()

    def on_accept(buf: Buffer) -> bool:
        line = buf.text.strip()
        if not line:
            return False

        if state["busy"]:
            if line.strip().lower() in ("/exit", "/quit"):
                append(f"\n{BLUE_BOLD}>{RESET} {line}\nStill indexing - please wait.\n\n")
            else:
                append(
                    f"\n{BLUE_BOLD}>{RESET} {line}\n"
                    "Still indexing, please wait until it finishes.\n\n"
                )
            return False

        if line.startswith("/"):
            parts = line.strip().split()
            if parts and parts[0].lower() == "/index" and store is not None:
                # Set synchronously so a command queued right behind /index
                # (fed together, e.g. from a paste) is blocked immediately -
                # the background task itself won't get a time slice until
                # this whole batch of keystrokes has been processed.
                state["busy"] = True
                get_app().create_background_task(run_index_async(line))
                return False

            msg, should_exit = handle_slash_command(
                line, state["last_results"], store, model_id=model_id
            )
            state["videos_count"] = len(store.list_videos())
            state["total_frames"] = store.stats().get("frames", 0)
            append(f"\n{BLUE_BOLD}>{RESET} {line}\n{msg}\n\n")
            if should_exit:
                get_app().exit()
            return False

        run_query(line)
        return False

    input_buffer = Buffer(
        history=FileHistory(str(HISTORY_FILE)), accept_handler=on_accept, multiline=False
    )
    input_window = Window(BufferControl(buffer=input_buffer))

    prompt_row = VSplit(
        [
            Window(FormattedTextControl(ANSI(f"{BLUE_BOLD}>{RESET} ")), dont_extend_width=True),
            input_window,
        ],
        height=1,
    )

    prompt_top_divider = Window(height=1, char="─", style="fg:#4b505f")
    prompt_bottom_divider = Window(height=1, char="─", style="fg:#4b505f")

    root = HSplit(
        [
            Window(FormattedTextControl(header_text), dont_extend_height=True),
            body_window,
            prompt_top_divider,
            prompt_row,
            prompt_bottom_divider,
            Window(FormattedTextControl(footer_text), height=1),
        ]
    )

    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("c-d")
    def _(event) -> None:
        event.app.exit()

    def scroll_by(lines: int) -> None:
        body_window.vertical_scroll = max(0, body_window.vertical_scroll + lines)

    # On Windows the console delivers wheel scroll as a raw MouseEvent that
    # Window's own default mouse handler already scrolls with (mouse_support
    # picks that up automatically); POSIX/vt100 terminals instead deliver it
    # as these key events, so bind them too as a fallback.
    @kb.add(Keys.ScrollUp)
    def _(event) -> None:
        scroll_by(-3)

    @kb.add(Keys.ScrollDown)
    def _(event) -> None:
        scroll_by(3)

    @kb.add("pageup")
    def _(event) -> None:
        scroll_by(-10)

    @kb.add("pagedown")
    def _(event) -> None:
        scroll_by(10)

    # A raw Application doesn't load PromptSession's default emacs/vi
    # bindings, so up/down never recalled input history until wired here.
    @kb.add("up")
    def _(event) -> None:
        input_buffer.history_backward()

    @kb.add("down")
    def _(event) -> None:
        input_buffer.history_forward()

    app = Application(
        layout=Layout(root, focused_element=input_window),
        key_bindings=kb,
        full_screen=True,
        mouse_support=True,
        input=input,
        output=output,
    )
    app_ref.append(app)
    app.run()
    print("\nFarewell. The seeing closes.")
    return state["body"]
