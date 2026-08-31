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
    " ███████████ ",
]

THRONE_BANNER_PLAIN = [
    "  #   #   #  ",
    " ### ### ### ",
    " ### ### ### ",
    " ########### ",
    "  #########  ",
    " ########### ",
]


def render_banner(
    model_id: str = "mobileclip2-s0",
    videos_count: int = 0,
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
    divider = "─" * 68 if use_unicode else "-" * 68

    tagline = '"From the Seat of Seeing, no moment remains hidden."'
    if use_plain:
        info_lines = [
            f"Amon Hen v{__version__} · {tagline}",
            f"Model: {model_id} (CPU)   Storage: sqlite-vec   Index: {videos_count} video(s)",
            "",
            "Type your search query, /open <num> to launch video, /cut <num> to export, or /help.",
            "",
            divider,
        ]
        combined = [f"{a} {b}".rstrip() for a, b in zip(art, info_lines, strict=True)]
        return "\n" + "\n".join(combined) + "\n"

    line1 = (
        f"\033[1;36mAmon Hen v{__version__}\033[0m  \033[90m·\033[0m  \033[3;90m{tagline}\033[0m"
    )
    line2 = (
        f"\033[90mModel:\033[0m \033[37m{model_id} (CPU)\033[0m   "
        f"\033[90mStorage:\033[0m \033[37msqlite-vec\033[0m   "
        f"\033[90mIndex:\033[0m \033[36m{videos_count} video(s)\033[0m"
    )
    line4 = (
        "\033[90mType your search query, \033[36m/open <num>\033[90m to play, "
        "\033[36m/cut <num>\033[90m to export, or \033[36m/help\033[90m.\033[0m"
    )
    info_lines = [
        line1,
        line2,
        "",
        line4,
        "",
        f"\033[90m{divider}\033[0m",
    ]
    combined = [f"\033[36m{a}\033[0m {b}".rstrip() for a, b in zip(art, info_lines, strict=True)]
    return "\n" + "\n".join(combined) + "\n"
