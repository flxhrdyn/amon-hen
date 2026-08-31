"""Theme styling, Tolkien aesthetics, turning verbs, and banner rendering."""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "█".encode(encoding)
        return "█" * filled + "░" * (width - filled)
    except (UnicodeEncodeError, LookupError):
        return "=" * filled + "-" * (width - filled)


THRONE_BANNER = [
    "  █   █   █  ",
    " ███ ███ ███ ",
    " ███ ███ ███ ",
    " ███████████ ",
    "  █████████  ",
]

THRONE_BANNER_PLAIN = [
    "  #   #   #  ",
    " ### ### ### ",
    " ### ### ### ",
    " ########### ",
    "  #########  ",
]


def render_banner(
    model_id: str = "mobileclip2-s0",
    videos_count: int = 0,
    total_frames: int = 0,
    dir_path: str = "",
    plain: bool = False,
) -> str:
    use_plain = plain or is_color_disabled()

    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    use_unicode = True
    try:
        "█".encode(encoding)
    except (UnicodeEncodeError, LookupError):
        use_unicode = False

    art = THRONE_BANNER if use_unicode else THRONE_BANNER_PLAIN
    divider = "─" * 80 if use_unicode else "-" * 80

    tagline = '"From the Seat of Seeing, no moment remains hidden."'
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

    if use_plain:
        info_lines = [
            f"Amon Hen v{__version__}  ·  {tagline}",
            f"Model: {model_id.upper()} (CPU)   Storage: sqlite-vec   {idx_str}",
            f"{path_display}",
            "",
            "",
        ]
        combined = [f"{a} {b}".rstrip() for a, b in zip(art, info_lines, strict=True)]
        return "\n" + "\n".join(combined) + "\n" + divider + "\n"

    line1 = f"\033[1;36mAmon Hen v{__version__}\033[0m  \033[90m·\033[0m  \033[97m{tagline}\033[0m"
    line2 = (
        f"\033[90mModel:\033[0m \033[97m{model_id.upper()} (CPU)\033[0m   "
        f"\033[90mStorage:\033[0m \033[97msqlite-vec\033[0m   "
        f"\033[90mIndex:\033[0m \033[36m{idx_str.replace('Index: ', '')}\033[0m"
    )
    line3 = f"\033[90m{path_display}\033[0m"
    info_lines = [
        line1,
        line2,
        line3,
        "",
        "",
    ]
    combined = [f"\033[36m{a}\033[0m {b}".rstrip() for a, b in zip(art, info_lines, strict=True)]
    return "\n" + "\n".join(combined) + "\n\033[90m" + divider + "\033[0m\n"
