"""Generate a realistic, pixel-perfect animated GIF of the Amon Hen TUI session."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from amonhen import __version__
from amonhen.theme import (
    BLUE,
    BLUE_BOLD,
    DIM,
    MUTED,
    RESET,
    WHITE,
    render_banner,
)

FONT_PATH = "C:/Windows/Fonts/cascadiamono.ttf"
FONT_SIZE = 14

BG_COLOR = "#0c0c0e"
HEADER_BAR_COLOR = "#18181c"
TAB_ACTIVE_COLOR = "#0c0c0e"
BLUE_COLOR = "#82aaff"  # Starlight Blue
WHITE_COLOR = "#ffffff"  # Pure White
MUTED_COLOR = "#8a90a0"  # Readable Muted Slate
DIVIDER_COLOR = "#2a2e3d"  # Subtle Horizontal Divider Line

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
    width_px: int = 860,
    height_px: int = 560,
) -> Image.Image:
    img = Image.new("RGB", (width_px, height_px), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    # Title Bar
    title_bar_height = 36
    draw.rectangle([0, 0, width_px, title_bar_height], fill=HEADER_BAR_COLOR)

    # Active Tab
    tab_w = 190
    draw.rectangle([10, 6, 10 + tab_w, title_bar_height], fill=TAB_ACTIVE_COLOR)
    tab_title = f">_ amon-hen v{__version__}"
    draw.text((22, 11), tab_title, font=font, fill="#c0caf5")

    # Window buttons
    draw.text((width_px - 85, 10), "─", font=font, fill="#999999")
    draw.rectangle([width_px - 55, 13, width_px - 45, 23], outline="#999999", width=1)
    draw.text((width_px - 25, 9), "✕", font=font, fill="#999999")

    # Content layout
    pad_x = 24
    curr_y = title_bar_height + 16
    line_h = 19

    # 1. Render Banner
    for raw_line in banner_text.splitlines():
        spans = parse_ansi_line(raw_line)
        curr_x = pad_x
        for text, color in spans:
            draw.text((curr_x, curr_y), text, font=font, fill=color)
            bbox = draw.textbbox((curr_x, curr_y), text, font=font)
            curr_x += bbox[2] - bbox[0]
        curr_y += line_h

    curr_y += 8

    # 2. Render Body
    visible_body = body_lines[-12:]
    for raw_line in visible_body:
        spans = parse_ansi_line(raw_line)
        curr_x = pad_x
        for text, color in spans:
            draw.text((curr_x, curr_y), text, font=font, fill=color)
            bbox = draw.textbbox((curr_x, curr_y), text, font=font)
            curr_x += bbox[2] - bbox[0]
        curr_y += line_h

    # 3. Render Input Prompt Area
    prompt_y = height_px - 72
    div_line = "─" * cols
    draw.text((pad_x, prompt_y - 20), div_line, font=font, fill=DIVIDER_COLOR)

    prompt_prefix = "Search> "
    draw.text((pad_x, prompt_y), prompt_prefix, font=font, fill=BLUE_COLOR)
    prefix_w = draw.textbbox((pad_x, prompt_y), prompt_prefix, font=font)[2] - pad_x

    draw.text((pad_x + prefix_w, prompt_y), prompt_input, font=font, fill=WHITE_COLOR)
    input_w = draw.textbbox((pad_x + prefix_w, prompt_y), prompt_input, font=font)[2] - (
        pad_x + prefix_w
    )

    if cursor:
        cursor_x = pad_x + prefix_w + input_w + 1
        draw.rectangle([cursor_x, prompt_y + 2, cursor_x + 8, prompt_y + 16], fill=BLUE_COLOR)

    draw.text((pad_x, prompt_y + 22), div_line, font=font, fill=DIVIDER_COLOR)

    # 4. Render Footer Shortcuts
    footer_y = height_px - 24
    draw.text((pad_x, footer_y), footer_text, font=font, fill=MUTED_COLOR)

    return img


def build_demo_gif():
    cols = 96
    width_px = 860
    height_px = 560

    banner_start = render_banner(
        videos_count=2,
        total_frames=441,
        model_id="mobileclip2-s0",
        width=cols,
        force_color=True,
        use_unicode=True,
    )

    footer = (
        "Shortcuts: [Enter] Search  [/open <n>] Play moment  [/cut <n>] Export clip  [/exit] Quit"
    )

    frames: list[Image.Image] = []
    durations: list[int] = []

    # Scene 1: Initial Start
    initial_body = [
        f"{BLUE_BOLD}* The Seat of Seeing is awake.{RESET} Describe any scene or spoken words.",
        "",
    ]
    for _ in range(2):
        frames.append(
            render_tui_frame(
                banner_start,
                initial_body,
                "",
                footer,
                cols,
                cursor=True,
                width_px=width_px,
                height_px=height_px,
            )
        )
        durations.append(400)

    # Scene 2: Type first search query `swords fight warriors in forest` (LOTR scene)
    query_1 = "swords fight warriors in forest"
    for i in range(1, len(query_1) + 1):
        frames.append(
            render_tui_frame(
                banner_start,
                initial_body,
                query_1[:i],
                footer,
                cols,
                cursor=True,
                width_px=width_px,
                height_px=height_px,
            )
        )
        durations.append(35)

    frames.append(
        render_tui_frame(
            banner_start,
            initial_body,
            query_1,
            footer,
            cols,
            cursor=False,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(350)

    # Scene 3: Display results for `swords fight warriors in forest`
    r_left1 = f"> {query_1}"
    r_right1 = "Saw in 21ms"
    r_pad1 = " " * max(1, cols - len(r_left1) - len(r_right1))
    q_line1 = f"{BLUE_BOLD}>{RESET} {query_1}{r_pad1}{MUTED}{r_right1}{RESET}"

    body_results_1 = initial_body + [
        q_line1,
        "",
        f"{BLUE_BOLD}#1   00:03:56.0 -> 00:04:52.0{RESET}              {DIM}[{BLUE_BOLD}███{DIM}░░░░░░░] {BLUE_BOLD}0.310{RESET}",
        f"{MUTED}File: battle-of-amon-hen.webm   Peak: 00:04:30.0{RESET}",
        f"{BLUE}=> Action: Type /open 1 to play moment (or /cut 1 to export){RESET}",
        "",
        f"{WHITE}#2   00:02:32.0 -> 00:02:56.0{RESET}              {DIM}[{BLUE}███{DIM}░░░░░░░] {BLUE}0.310{RESET}",
        f"{MUTED}File: battle-of-amon-hen.webm   Peak: 00:02:45.0{RESET}",
        "",
    ]

    frames.append(
        render_tui_frame(
            banner_start,
            body_results_1,
            "",
            footer,
            cols,
            cursor=True,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(2200)

    # Scene 4: Type `/open 1` to play clip
    cmd_open = "/open 1"
    for i in range(1, len(cmd_open) + 1):
        frames.append(
            render_tui_frame(
                banner_start,
                body_results_1,
                cmd_open[:i],
                footer,
                cols,
                cursor=True,
                width_px=width_px,
                height_px=height_px,
            )
        )
        durations.append(45)

    body_open = body_results_1 + [
        f"{BLUE_BOLD}>{RESET} {cmd_open}",
        f"{BLUE_BOLD}=> Launching media player at 00:04:30.0 (battle-of-amon-hen.webm)...{RESET}",
        "",
    ]

    frames.append(
        render_tui_frame(
            banner_start,
            body_open,
            "",
            footer,
            cols,
            cursor=True,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(1800)

    # Scene 5: Type second search query `a person holding an umbrella` (CCTV real-world use)
    query_2 = "a person holding an umbrella"
    for i in range(1, len(query_2) + 1):
        frames.append(
            render_tui_frame(
                banner_start,
                body_open,
                query_2[:i],
                footer,
                cols,
                cursor=True,
                width_px=width_px,
                height_px=height_px,
            )
        )
        durations.append(35)

    frames.append(
        render_tui_frame(
            banner_start,
            body_open,
            query_2,
            footer,
            cols,
            cursor=False,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(350)

    # Scene 6: Display results for CCTV query
    r_left2 = f"> {query_2}"
    r_right2 = "Saw in 19ms"
    r_pad2 = " " * max(1, cols - len(r_left2) - len(r_right2))
    q_line2 = f"{BLUE_BOLD}>{RESET} {query_2}{r_pad2}{MUTED}{r_right2}{RESET}"

    body_results_2 = body_open + [
        q_line2,
        "",
        f"{BLUE_BOLD}#1   00:00:37.0 -> 00:01:06.0{RESET}              {DIM}[{BLUE_BOLD}███{DIM}░░░░░░░] {BLUE_BOLD}0.261{RESET}",
        f"{MUTED}File: cctv-people-demo.webm   Peak: 00:00:48.0{RESET}",
        f"{BLUE}=> Action: Type /open 1 to play moment (or /cut 1 to export){RESET}",
        "",
        f"{WHITE}#2   00:00:04.0 -> 00:00:19.0{RESET}              {DIM}[{BLUE}██{DIM}░░░░░░░░] {BLUE}0.247{RESET}",
        f"{MUTED}File: cctv-people-demo.webm   Peak: 00:00:12.0{RESET}",
        "",
    ]

    frames.append(
        render_tui_frame(
            banner_start,
            body_results_2,
            "",
            footer,
            cols,
            cursor=True,
            width_px=width_px,
            height_px=height_px,
        )
    )
    durations.append(2600)

    # Save GIF
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
