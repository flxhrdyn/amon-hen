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
            t0 = f"{int(start_s // 60):02d}:{start_s % 60:04.1f}"
            t1 = f"{int(end_s // 60):02d}:{end_s % 60:04.1f}"
            time_str = f"{t0} - {t1}"
        else:
            time_str = f"{int(start_s // 60):02d}:{start_s % 60:04.1f}              "
        bar = format_score_bar(seg.score, width=8)
        lines.append(f" {i:>2}. {time_str}  {bar} {seg.score:.3f}  {name}")
    return "\n".join(lines)


def handle_slash_command(
    cmd_line: str,
    last_results: list[Segment],
    store: Store | None,
) -> tuple[str, bool]:
    parts = cmd_line.strip().split()
    if not parts:
        return "", False
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
