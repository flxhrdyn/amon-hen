"""Generate a realistic, pixel-perfect animated GIF of the Amon Hen TUI session."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from amonhen import __version__
from amonhen.theme import render_banner

FONT_PATH = "C:/Windows/Fonts/cascadiamono.ttf"
FONT_SIZE = 14
BG_COLOR = "#1a1b26"
FG_COLOR = "#c0caf5"
BLUE_COLOR = "#7aa2f7"
CYAN_COLOR = "#7dcfff"
GREEN_COLOR = "#9ece6a"
YELLOW_COLOR = "#e0af68"
MUTED_COLOR = "#565f89"
WHITE_COLOR = "#ffffff"
DIVIDER_COLOR = "#414868"
HEADER_BAR_COLOR = "#16161e"
DOT_RED = "#f7768e"
DOT_YELLOW = "#e0af68"
DOT_GREEN = "#9ece6a"

OUT_PATH = Path("demo/demo.gif")


def parse_ansi_spans(text: str) -> list[tuple[str, str]]:
    """Simple parser that converts our theme ANSI sequences to colored spans."""
    color_map = {
        "\033[1;36m": CYAN_COLOR,
        "\033[36m": CYAN_COLOR,
        "\033[1;34m": BLUE_COLOR,
        "\033[34m": BLUE_COLOR,
        "\033[97m": WHITE_COLOR,
        "\033[1;97m": WHITE_COLOR,
        "\033[90m": MUTED_COLOR,
        "\033[32m": GREEN_COLOR,
        "\033[33m": YELLOW_COLOR,
        "\033[0m": FG_COLOR,
    }

    current_color = FG_COLOR
    spans = []
    i = 0
    buffer = ""

    while i < len(text):
        if text[i] == "\033" and "[" in text[i : i + 3]:
            end = text.find("m", i)
            if end != -1:
                if buffer:
                    spans.append((buffer, current_color))
                    buffer = ""
                code = text[i : end + 1]
                current_color = color_map.get(code, FG_COLOR)
                i = end + 1
                continue
        buffer += text[i]
        i += 1

    if buffer:
        spans.append((buffer, current_color))

    return spans


def render_tui_frame(
    banner_text: str,
    body_lines: list[str],
    prompt_input: str,
    footer_text: str,
    cursor: bool = True,
    width_px: int = 900,
    height_px: int = 580,
) -> Image.Image:
    img = Image.new("RGBA", (width_px, height_px), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    # Draw Terminal Title Bar
    title_bar_height = 36
    draw.rectangle([0, 0, width_px, title_bar_height], fill=HEADER_BAR_COLOR)
    # macOS style window buttons
    draw.ellipse([14, 12, 24, 22], fill=DOT_RED)
    draw.ellipse([34, 12, 44, 22], fill=DOT_YELLOW)
    draw.ellipse([54, 12, 64, 22], fill=DOT_GREEN)

    # Title text
    title = f"amon-hen v{__version__} · Terminal"
    draw.text((width_px // 2 - 80, 10), title, font=font, fill=MUTED_COLOR)

    # Terminal layout content
    pad_x = 18
    pad_y = title_bar_height + 12
    line_h = 20

    # 1. Render Banner
    current_y = pad_y
    for banner_line in banner_text.split("\n"):
        spans = parse_ansi_spans(banner_line)
        x = pad_x
        for span_text, span_color in spans:
            draw.text((x, current_y), span_text, font=font, fill=span_color)
            bbox = font.getbbox(span_text)
            x += bbox[2] - bbox[0]
        current_y += line_h

    current_y += 6

    # 2. Render Body scrollback (up to bottom)
    body_max_y = height_px - 75
    for bline in body_lines[-16:]:
        if current_y > body_max_y:
            break
        spans = parse_ansi_spans(bline)
        x = pad_x
        for span_text, span_color in spans:
            draw.text((x, current_y), span_text, font=font, fill=span_color)
            bbox = font.getbbox(span_text)
            x += bbox[2] - bbox[0]
        current_y += line_h

    # 3. Render Textbox (Top divider + prompt + Bottom divider)
    box_y = height_px - 56
    divider_str = "─" * 96
    draw.text((pad_x, box_y - 18), divider_str, font=font, fill=DIVIDER_COLOR)

    prompt_prefix = "> "
    draw.text((pad_x, box_y), prompt_prefix, font=font, fill=CYAN_COLOR)
    prefix_w = font.getbbox(prompt_prefix)[2]

    draw.text((pad_x + prefix_w, box_y), prompt_input, font=font, fill=FG_COLOR)
    input_w = font.getbbox(prompt_input)[2] if prompt_input else 0

    if cursor:
        cur_x = pad_x + prefix_w + input_w + 2
        draw.rectangle([cur_x, box_y + 2, cur_x + 8, box_y + 16], fill=CYAN_COLOR)

    draw.text((pad_x, box_y + 18), divider_str, font=font, fill=DIVIDER_COLOR)

    # 4. Render Footer
    footer_y = height_px - 18
    spans = parse_ansi_spans(footer_text)
    x = pad_x
    for span_text, span_color in spans:
        draw.text((x, footer_y), span_text, font=font, fill=span_color)
        bbox = font.getbbox(span_text)
        x += bbox[2] - bbox[0]

    return img.convert("RGB")


def build_demo_gif() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    banner_0 = render_banner(
        model_id="mobileclip2-s0",
        videos_count=0,
        total_frames=0,
        dir_path="~/videos/demo",
        width=78,
    )
    banner_1 = render_banner(
        model_id="mobileclip2-s0",
        videos_count=1,
        total_frames=142,
        dir_path="~/videos/demo",
        width=78,
    )

    footer = "\033[90m[Enter] Submit  ·  /index <dir>  ·  /open <id>  ·  /cut <id>  ·  /exit                        MOBILECLIP2-S0 · CPU\033[0m"

    initial_body = [
        "\033[90mType a query in plain English to search your indexed videos.\033[0m",
        "",
        "\033[90m  /index <path>   index new videos\033[0m",
        "\033[90m  /open <id>      play a result\033[0m",
        "\033[90m  /help           show all commands\033[0m",
    ]

    # Scene 1: Initial Screen (1.2s)
    f = render_tui_frame(banner_0, initial_body, "", footer, cursor=True)
    frames.append(f)
    durations.append(1200)

    # Scene 2: Type `/index demo/cctv-people-demo.webm`
    cmd_index = "/index demo/cctv-people-demo.webm"
    for i in range(1, len(cmd_index) + 1):
        f = render_tui_frame(banner_0, initial_body, cmd_index[:i], footer, cursor=True)
        frames.append(f)
        durations.append(45)

    # Pause before enter
    frames.append(render_tui_frame(banner_0, initial_body, cmd_index, footer, cursor=False))
    durations.append(400)

    # Scene 3: Progress animation
    body_indexing = [
        f"\033[1;36m>\033[0m {cmd_index}",
        "",
    ]
    for p in [0.15, 0.40, 0.70, 0.95]:
        filled = int(30 * p)
        bar = "█" * filled + "░" * (30 - filled)
        prog_line = f"* Gazing cctv-people-demo.webm... [\033[1;36m{bar}\033[0m]"
        f = render_tui_frame(
            banner_0,
            body_indexing + [prog_line],
            "",
            footer,
            cursor=False,
        )
        frames.append(f)
        durations.append(400)

    # Finish indexing
    body_after_index = [
        f"\033[1;36m>\033[0m {cmd_index}",
        "\033[1;36m* Unveiled 1 video(s) into database (Index: 1 videos, 142 frames).\033[0m",
        "",
    ]
    f = render_tui_frame(banner_1, body_after_index, "", footer, cursor=True)
    frames.append(f)
    durations.append(800)

    # Scene 4: Type search query `a person holding an umbrella`
    query_1 = "a person holding an umbrella"
    for i in range(1, len(query_1) + 1):
        f = render_tui_frame(banner_1, body_after_index, query_1[:i], footer, cursor=True)
        frames.append(f)
        durations.append(45)

    frames.append(render_tui_frame(banner_1, body_after_index, query_1, footer, cursor=False))
    durations.append(400)

    # Scene 5: Display search results
    body_results_1 = body_after_index + [
        f"\033[1;36m>\033[0m {query_1}                                                   \033[90mSaw in 18ms\033[0m",
        "",
        "\033[1;36m#1   00:00:37.0 -> 00:01:06.0\033[0m              \033[36m[████████░░] 0.261\033[0m",
        "\033[90mFile: cctv-people-demo.webm   Peak: 00:00:48.0\033[0m",
        "\033[36m=> Action: Type /open 1 to play moment (or /cut 1 to export)\033[0m",
        "",
        "\033[1;97m#2   00:00:02.0 -> 00:00:14.0\033[0m              \033[1;97m[█████░░░░░] 0.174\033[0m",
        "\033[90mFile: cctv-people-demo.webm   Peak: 00:00:07.0\033[0m",
        "",
    ]
    f = render_tui_frame(banner_1, body_results_1, "", footer, cursor=True)
    frames.append(f)
    durations.append(2500)

    # Scene 6: Type `/open 1`
    cmd_open = "/open 1"
    for i in range(1, len(cmd_open) + 1):
        f = render_tui_frame(banner_1, body_results_1, cmd_open[:i], footer, cursor=True)
        frames.append(f)
        durations.append(60)

    # Execute /open 1
    body_open = body_results_1 + [
        f"\033[1;36m>\033[0m {cmd_open}",
        "\033[1;36m=> Launching media player at 00:48.0 (cctv-people-demo.webm)...\033[0m",
        "",
    ]
    f = render_tui_frame(banner_1, body_open, "", footer, cursor=True)
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
    print(f"Generated demo GIF ({len(frames)} frames) -> {OUT_PATH}")


if __name__ == "__main__":
    build_demo_gif()
