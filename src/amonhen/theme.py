"""Theme styling, Tolkien aesthetics, turning verbs, and banner rendering."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from amonhen import __version__

# Fixed truecolor palette so the TUI looks the same regardless of the
# user's terminal color scheme, instead of the 16-color ANSI codes whose
# actual hue depends on that scheme.
BLUE = "\033[38;2;130;170;255m"
BLUE_BOLD = "\033[1;38;2;130;170;255m"
WHITE = "\033[38;2;240;243;248m"
WHITE_BOLD = "\033[1;38;2;240;243;248m"
MUTED = "\033[38;2;110;115;130m"
DIM = "\033[38;2;75;80;95m"
RESET = "\033[0m"

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


def format_timestamp(ts_ms: int) -> str:
    total_seconds, milliseconds = divmod(int(ts_ms), 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds // 100}"


def format_score_bar(score: float, width: int = 10) -> str:
    clamped = max(0.0, min(1.0, score))
    filled = int(round(clamped * width))
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "█".encode(encoding)
        return "█" * filled + "░" * (width - filled)
    except (UnicodeEncodeError, LookupError):
        return "=" * filled + "-" * (width - filled)


THRONE_BANNER = [
    "  ▄  █  ▄  ",
    " ▄█▀▄█▄▀█▄ ",
    " ▒███████▒ ",
]

THRONE_BANNER_PLAIN = [
    "  .  |  .  ",
    " / \\/|\\/ \\ ",
    " [=======] ",
]


def render_banner(
    model_id: str = "mobileclip2-s0",
    videos_count: int = 0,
    total_frames: int = 0,
    dir_path: str = "",
    plain: bool = False,
    width: int = 78,
    use_unicode: bool | None = None,
) -> str:
    use_plain = plain or is_color_disabled()

    if use_unicode is None:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        use_unicode = True
        try:
            "█".encode(encoding)
            "╭".encode(encoding)
        except (UnicodeEncodeError, LookupError):
            use_unicode = False

    art_plain = THRONE_BANNER if use_unicode else THRONE_BANNER_PLAIN
    art = [f"{BLUE}{row}{RESET}" for row in art_plain] if not use_plain else art_plain
    tl, tr, bl, br, h, v = (
        ("╭", "╮", "╰", "╯", "─", "│")
        if use_unicode
        else (
            "+",
            "+",
            "+",
            "+",
            "-",
            "|",
        )
    )

    if videos_count > 0:
        idx_str = f"Index: {videos_count} video ({total_frames} frames)"
    else:
        idx_str = "Index: Ready (0 videos)"

    path_display = dir_path or os.getcwd()
    try:
        home = str(Path.home())
        if path_display.startswith(home):
            path_display = "~" + path_display[len(home) :]
    except Exception:
        pass
    path_display = path_display.replace("\\", "/")

    title = f" Amon Hen v{__version__} "
    target_width = max(40, width)
    inner_width = target_width - 4
    art_width = len(art_plain[0])
    max_text_w = max(10, inner_width - art_width - 1)

    if len(path_display) > max_text_w:
        path_display = "..." + path_display[-(max_text_w - 3) :]

    if target_width >= 86:
        plain_lines = [
            '"From the Seat of Seeing, no moment remains hidden."',
            f"Model: {model_id.upper()} (CPU)   Storage: sqlite-vec   {idx_str}",
            path_display,
        ]
    elif target_width >= 65:
        plain_lines = [
            '"From the Seat of Seeing, no moment remains hidden."',
            f"Model: {model_id.upper()}   {idx_str}",
            path_display,
        ]
    else:
        plain_lines = [
            f"{model_id.upper()} (CPU)",
            idx_str,
            path_display,
        ]

    for i in range(len(plain_lines)):
        if len(plain_lines[i]) > max_text_w:
            plain_lines[i] = plain_lines[i][: max_text_w - 3] + "..."

    styled_lines = (
        [
            f"{WHITE}{plain_lines[0]}{RESET}",
            f"{MUTED}{plain_lines[1]}{RESET}",
            f"{MUTED}{plain_lines[2]}{RESET}",
        ]
        if not use_plain
        else plain_lines
    )

    box_width = target_width
    if len(title) > box_width - 4:
        title = " AmonHen "

    border_color = BLUE if not use_plain else ""
    reset = RESET if not use_plain else ""

    top_fill = h * max(1, box_width - 2 - len(title))
    lines = [f"{border_color}{tl}{title}{top_fill}{tr}{reset}"]

    for art_row, plain_row, styled_row in zip(art, plain_lines, styled_lines, strict=True):
        content = f"{art_row} {styled_row}"
        pad = " " * max(0, inner_width - art_width - 1 - len(plain_row))
        lines.append(f"{border_color}{v}{reset} {content}{pad} {border_color}{v}{reset}")

    lines.append(f"{border_color}{bl}{h * (box_width - 2)}{br}{reset}")
    return "\n".join(lines)
