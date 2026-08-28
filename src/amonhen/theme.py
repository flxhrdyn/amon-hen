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


def render_banner(
    model_id: str = "mobileclip2-s2",
    videos_count: int = 0,
    plain: bool = False,
) -> str:
    use_plain = plain or is_color_disabled()
    title = "  Amon Hen  "
    tagline = '  "From the Seat of Seeing, no moment remains hidden."  '
    status = f"  v{__version__} | model: {model_id} | indexed: {videos_count} video(s)  "

    if use_plain:
        return f"\n{title}\n{tagline}\n{status}\n"

    # Subtle ANSI coloring: 33 = muted gold, 90 = stone gray, 36 = pale blue
    return f"\n\033[1;33m{title}\033[0m\n\033[3;90m{tagline}\033[0m\n\033[36m{status}\033[0m\n"
