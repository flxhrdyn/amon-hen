"""Interactive REPL session for AmonHen."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from amonhen.cutter import cut_video_segment
from amonhen.player import open_video_at
from amonhen.segment import Segment
from amonhen.theme import format_score_bar, get_turning_verb, render_banner

if TYPE_CHECKING:
    from amonhen.store import Store


HISTORY_FILE = Path.home() / ".amonhen" / "history"


def format_segment_results(segments: list[Segment]) -> str:
    if not segments:
        return "No matching moments found."

    blocks = []
    for i, seg in enumerate(segments, start=1):
        name = Path(seg.video_path).name
        start_s = seg.start_ms / 1000.0
        end_s = seg.end_ms / 1000.0
        peak_s = seg.best_ts_ms / 1000.0

        t0 = f"{int(start_s // 60):02d}:{start_s % 60:04.1f}"
        t1 = f"{int(end_s // 60):02d}:{end_s % 60:04.1f}"
        time_str = f"{t0} -> {t1}" if seg.start_ms < seg.end_ms else f"{t0}              "
        peak_str = f"{int(peak_s // 60):02d}:{peak_s % 60:04.1f}"

        bar = format_score_bar(seg.score, width=10)
        bar_str = f"[{bar}] {seg.score:.3f}"

        if i == 1:
            header = f"\033[1;36m#{i}   {time_str:<23}\033[0m              \033[36m{bar_str}\033[0m"
            meta = f"\033[90mFile: {name}   Peak: {peak_str}\033[0m"
            action = (
                f"\033[36m=> Action: Type /open {i} to play moment (or /cut {i} to export)\033[0m"
            )
            blocks.append(f"{header}\n{meta}\n{action}")
        else:
            header = f"\033[1;37m#{i}   {time_str:<23}\033[0m              \033[37m{bar_str}\033[0m"
            meta = f"\033[90mFile: {name}   Peak: {peak_str}\033[0m"
            blocks.append(f"{header}\n{meta}")

    return "\n\n".join(blocks)


def handle_slash_command(
    cmd_line: str,
    last_results: list[Segment],
    store: Store | None,
    model_id: str = "mobileclip2-s0",
) -> tuple[str, bool]:
    parts = cmd_line.strip().split()
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

    if cmd == "/index" and store:
        if len(parts) < 2:
            return "Usage: /index <path_to_video_or_dir>", False
        target_path = Path(parts[1])
        if not target_path.exists():
            return f"Path does not exist: {target_path}", False

        from amonhen.pipeline import index_videos
        from amonhen.progress import RichReporter

        reporter = RichReporter()
        try:
            print(f"\033[1;36m* Gazing across {target_path}...\033[0m")
            indexed, skipped = index_videos(
                paths=[target_path],
                store=store,
                model_id=model_id,
                reporter=reporter,
            )
            total_vids = len(store.list_videos())
            total_frames = store.stats().get("frames", 0)
            msg = (
                f"\033[1;36m* Unveiled {indexed} video(s) into database "
                f"(Index: {total_vids} videos, {total_frames} frames).\033[0m"
            )
            return msg, False
        except Exception as e:
            return f"Indexing failed: {e}", False

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
            return f"\033[1;36m=> Launching media player at {time_str} ({name})...\033[0m", False
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
                f"\033[1;36m=> Exported clip #{idx} ({t0} - {t1}) to:\n  {clip_path}\033[0m",
                False,
            )
        except Exception as e:
            return f"Could not export clip: {e}", False
    return f"Result #{idx} not found. Last search returned {len(last_results)} result(s).", False


def run_interactive_session(
    store: Store,
    text_encoder,
    model_id: str = "mobileclip2-s0",
) -> None:
    from prompt_toolkit.formatted_text import HTML

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(HISTORY_FILE)))

    videos_count = len(store.list_videos())
    total_frames = store.stats().get("frames", 0)
    print(
        render_banner(
            model_id=model_id,
            videos_count=videos_count,
            total_frames=total_frames,
        )
    )

    def bottom_toolbar():
        left = (
            "<style color='#6e7382'>[Enter] Submit  ·  /index &lt;dir&gt;  ·  "
            "/open &lt;id&gt;  ·  /cut &lt;id&gt;  ·  /exit</style>"
        )
        right = f"<style color='#4b505f'>{model_id.upper()} · CPU</style>"
        spaces = " " * 16
        return HTML(f"{left}{spaces}{right}")

    last_results: list[Segment] = []

    while True:
        try:
            line = session.prompt("> ", bottom_toolbar=bottom_toolbar).strip()
            if not line:
                continue

            if line.startswith("/"):
                msg, should_exit = handle_slash_command(
                    line, last_results, store, model_id=model_id
                )
                print(msg)
                if should_exit:
                    break
                continue

            # Natural search query
            from amonhen.pipeline import search

            t0 = time.perf_counter()
            last_results = search(line, store, text_encoder, limit=5)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            verb = get_turning_verb().capitalize()
            print(f"\033[90m{verb} in {elapsed_ms:.0f}ms\033[0m\n")
            print(format_segment_results(last_results))
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nFarewell. The seeing closes.")
            break
