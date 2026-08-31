"""Generate a realistic, pixel-perfect animated GIF of the Amon Hen TUI session."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from amonhen import __version__
from amonhen.theme import (
    BLUE,
    BLUE_BOLD,
    MUTED,
    RESET,
    WHITE,
    render_banner,
)

FONT_PATH = "C:/Windows/Fonts/cascadiamono.ttf"
FONT_SIZE = 14

# Exact True Dark + Starlight Blue palette from authentic Windows Terminal / TUI session
BG_COLOR = "#0c0c0e"
HEADER_BAR_COLOR = "#18181c"
TAB_ACTIVE_COLOR = "#0c0c0e"
BLUE_COLOR = "#82aaff"  # Starlight Blue
WHITE_COLOR = "#ffffff"  # Pure White
MUTED_COLOR = "#8a90a0"  # Readable Muted Slate
DIVIDER_COLOR = "#2a2e3d"  # Subtle Horizontal Divider Line
DOT_CLOSE = "#e81123"

OUT_PATH = Path("demo/demo.gif")

ANSI_RE = re.compile(r"\x1b\[([0-9;]+)m")


def parse_ansi_line(line: str) -> list[tuple[str, str]]:
    spans = []
    current_color = WHITE_COLOR
    last_idx = 0

    for match in ANSI_RE.finditer(line):
        text_chunk = line[last_idx : match.start()]
        if text_chunk:
            spans.append((text_chunk, current_color))
        code_str = match.group(1)
        if code_str == "0":
            current_color = WHITE_COLOR
        elif "130;170;255" in code_str or "36" in code_str or "34" in code_str:
            current_color = BLUE_COLOR
        elif "240;243;248" in code_str or "97" in code_str:
            current_color = WHITE_COLOR
        elif "110;115;130" in code_str or "90" in code_str:
            current_color = MUTED_COLOR
        elif "75;80;95" in code_str:
            current_color = DIVIDER_COLOR
        last_idx = match.end()

    tail = line[last_idx:]
    if tail:
        spans.append((tail, current_color))
    return spans


def render_tui_frame(
    banner_text: str,
    body_lines: list[str],
    prompt_input: str,
    footer_text: str,
    cols: int,
    cursor: bool = True,
    width_px: int = 836,
    height_px: int = 540,
) -> Image.Image:
    img = Image.new("RGB", (width_px, height_px), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    # Draw Windows Terminal Title Bar
    title_bar_height = 36
    draw.rectangle([0, 0, width_px, title_bar_height], fill=HEADER_BAR_COLOR)

    # Active Tab
    tab_w = 180
    draw.rectangle([10, 6, 10 + tab_w, title_bar_height], fill=TAB_ACTIVE_COLOR)
    # Terminal tab title
    tab_title = f">_ amon-hen v{__version__}"
    draw.text((22, 11), tab_title, font=font, fill="#c0caf5")

    # Windows-style window buttons on top right
    draw.text((width_px - 85, 10), "─", font=font, fill="#999999")
    draw.rectangle([width_px - 55, 13, width_px - 45, 23], outline="#999999", width=1)
    draw.text((width_px - 25, 9), "✕", font=font, fill="#999999")

    # Content layout
    pad_x = 18
    current_y = title_bar_height + 12
    line_h = 20

    # 1. Render Header Banner (Themed Box with Eagle Silhouette)
    for banner_line in banner_text.split("\n"):
        spans = parse_ansi_line(banner_line)
        x = pad_x
        for span_text, span_color in spans:
            draw.text((x, current_y), span_text, font=font, fill=span_color)
            x += font.getlength(span_text)
        current_y += line_h

    current_y += 10

    # 2. Render Scrollback Body
    body_max_y = height_px - 70
    for bline in body_lines[-14:]:
        if current_y > body_max_y:
            break
        spans = parse_ansi_line(bline)
        x = pad_x
        for span_text, span_color in spans:
            draw.text((x, current_y), span_text, font=font, fill=span_color)
            x += font.getlength(span_text)
        current_y += line_h

    # 3. Render Textbox (Top divider + prompt + Bottom divider)
    box_y = height_px - 54
    divider_str = "─" * cols
    draw.text((pad_x, box_y - 18), divider_str, font=font, fill=DIVIDER_COLOR)

    prompt_prefix = "> "
    draw.text((pad_x, box_y), prompt_prefix, font=font, fill=BLUE_COLOR)
    prefix_w = font.getlength(prompt_prefix)

    draw.text((pad_x + prefix_w, box_y), prompt_input, font=font, fill=WHITE_COLOR)
    input_w = font.getlength(prompt_input) if prompt_input else 0

    if cursor:
        cur_x = pad_x + prefix_w + input_w + 2
        draw.rectangle([cur_x, box_y + 2, cur_x + 8, box_y + 16], fill=BLUE_COLOR)

    draw.text((pad_x, box_y + 18), divider_str, font=font, fill=DIVIDER_COLOR)

    # 4. Render Footer
    footer_y = height_px - 16
    spans = parse_ansi_line(footer_text)
    x = pad_x
    for span_text, span_color in spans:
        draw.text((x, footer_y), span_text, font=font, fill=span_color)
        x += font.getlength(span_text)

    return img


def build_demo_gif() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    cols = 100
    pad_x = 18
    width_px = int(cols * 8.0 + 2 * pad_x)
    height_px = 540

    banner_0 = render_banner(
        model_id="mobileclip2-s0",
        videos_count=0,
        total_frames=0,
        dir_path="~/videos/demo",
        width=cols,
        use_unicode=True,
        force_color=True,
    )
    banner_1 = render_banner(
        model_id="mobileclip2-s0",
        videos_count=1,
        total_frames=142,
        dir_path="~/videos/demo",
        width=cols,
        use_unicode=True,
        force_color=True,
    )

    left = "[Enter] Submit  ·  /index <dir>  ·  /open <id>  ·  /cut <id>  ·  /exit"
    right = "MOBILECLIP2-S0 · CPU"
    pad = " " * max(1, cols - len(left) - len(right))
    footer = f"{MUTED}{left}{pad}{right}{RESET}"

    initial_body = [
        f"{MUTED}Type a query in plain English to search your indexed videos.{RESET}",
        "",
        f"{MUTED}  /index <path>   index new videos{RESET}",
        f"{MUTED}  /open <id>      play a result{RESET}",
        f"{MUTED}  /help           show all commands{RESET}",
    ]

    # Scene 1: Initial Screen (1.2s)
    f = render_tui_frame(
        banner_0,
        initial_body,
        "",
        footer,
        cols,
        cursor=True,
        width_px=width_px,
        height_px=height_px,
    )
    frames.append(f)
    durations.append(1200)

    # Scene 2: Type `/index demo/cctv-people-demo.webm`
    cmd_index = "/index demo/cctv-people-demo.webm"
    for i in range(1, len(cmd_index) + 1):
        f = render_tui_frame(
            banner_0,
            initial_body,
            cmd_index[:i],
            footer,
            cols,
            cursor=True,
            width_px=width_px,
            height_px=height_px,
        )
        frames.append(f)
        durations.append(40)

    # Pause before enter
    frames.append(
        render_tui_frame(
            banner_0,
            initial_body,
            cmd_index,
            footer,
            cols,
            cursor=False,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(400)

    # Scene 3: Progress animation
    body_indexing = [
        f"{BLUE_BOLD}>{RESET} {cmd_index}",
        "",
    ]
    for p in [0.15, 0.40, 0.70, 0.95]:
        filled = int(30 * p)
        bar = "█" * filled + "░" * (30 - filled)
        prog_line = f"* Gazing cctv-people-demo.webm... [{BLUE}{bar}{RESET}]"
        f = render_tui_frame(
            banner_0,
            body_indexing + [prog_line],
            "",
            footer,
            cols,
            cursor=False,
            width_px=width_px,
            height_px=height_px,
        )
        frames.append(f)
        durations.append(350)

    # Finish indexing
    body_after_index = [
        f"{BLUE_BOLD}>{RESET} {cmd_index}",
        f"{BLUE_BOLD}* Unveiled 1 video(s) into database (Index: 1 videos, 142 frames).{RESET}",
        "",
    ]
    f = render_tui_frame(
        banner_1,
        body_after_index,
        "",
        footer,
        cols,
        cursor=True,
        width_px=width_px,
        height_px=height_px,
    )
    frames.append(f)
    durations.append(800)

    # Scene 4: Type search query `a person holding an umbrella`
    query_1 = "a person holding an umbrella"
    for i in range(1, len(query_1) + 1):
        f = render_tui_frame(
            banner_1,
            body_after_index,
            query_1[:i],
            footer,
            cols,
            cursor=True,
            width_px=width_px,
            height_px=height_px,
        )
        frames.append(f)
        durations.append(40)

    frames.append(
        render_tui_frame(
            banner_1,
            body_after_index,
            query_1,
            footer,
            cols,
            cursor=False,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(400)

    # Scene 5: Display search results
    r_left = f"> {query_1}"
    r_right = "Saw in 18ms"
    r_pad = " " * max(1, cols - len(r_left) - len(r_right))
    query_line = f"{BLUE_BOLD}>{RESET} {query_1}{r_pad}{MUTED}{r_right}{RESET}"

    body_results_1 = body_after_index + [
        query_line,
        "",
        f"{BLUE_BOLD}#1   00:00:37.0 -> 00:01:06.0{RESET}              {BLUE}[████████░░] 0.261{RESET}",
        f"{MUTED}File: cctv-people-demo.webm   Peak: 00:00:48.0{RESET}",
        f"{BLUE}=> Action: Type /open 1 to play moment (or /cut 1 to export){RESET}",
        "",
        f"{WHITE}#2   00:00:02.0 -> 00:00:14.0{RESET}              {BLUE}[█████░░░░░] 0.174{RESET}",
        f"{MUTED}File: cctv-people-demo.webm   Peak: 00:00:07.0{RESET}",
        "",
    ]
    f = render_tui_frame(
        banner_1,
        body_results_1,
        "",
        footer,
        cols,
        cursor=True,
        width_px=width_px,
        height_px=height_px,
    )
    frames.append(f)
    durations.append(2500)

    # Scene 6: Type `/open 1`
    cmd_open = "/open 1"
    for i in range(1, len(cmd_open) + 1):
        f = render_tui_frame(
            banner_1,
            body_results_1,
            cmd_open[:i],
            footer,
            cols,
            cursor=True,
            width_px=width_px,
            height_px=height_px,
        )
        frames.append(f)
        durations.append(50)

    # Execute /open 1
    body_open = body_results_1 + [
        f"{BLUE_BOLD}>{RESET} {cmd_open}",
        f"{BLUE_BOLD}=> Launching media player at 00:48.0 (cctv-people-demo.webm)...{RESET}",
        "",
    ]
    f = render_tui_frame(
        banner_1, body_open, "", footer, cols, cursor=True, width_px=width_px, height_px=height_px
    )
    frames.append(f)
    durations.append(2000)

    # Save animated GIF
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(
        f"Generated demo GIF ({len(frames)} frames, {cols} cols, width: {width_px}px) -> {OUT_PATH}"
    )


if __name__ == "__main__":
    build_demo_gif()
