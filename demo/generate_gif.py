"""Render pixel-perfect Claude Code CLI demo GIF with Tolkien ASCII art header and zero broken glyphs."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 580

# Clean Dark Theme
BG_COLOR = (24, 24, 27)          # #18181B zinc-900
TITLE_BG = (18, 18, 20)          # #121214
BORDER_COLOR = (45, 45, 52)

PROMPT_VIOLET = (192, 132, 252)  # Claude Code violet
GOLD_ACCENT = (250, 204, 21)     # Muted Tolkien gold
CYAN_TIME = (56, 189, 248)       # Starlight cyan
GREEN_ACCENT = (74, 222, 128)    # Terminal green
WHITE_TEXT = (244, 244, 245)     # Primary text
MUTED_GRAY = (140, 145, 160)     # Metadata gray
TREE_LINE = (82, 82, 91)         # Tree lines
BAR_EMPTY = (42, 44, 54)         # Track background

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font_main = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font_main = font_bold = font_small = ImageFont.load_default()


def create_base_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Titlebar
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COLOR)

    # macOS window controls
    draw.ellipse([14, 10, 24, 20], fill=(239, 68, 68))
    draw.ellipse([30, 10, 40, 20], fill=(245, 158, 11))
    draw.ellipse([46, 10, 56, 20], fill=(34, 197, 94))

    draw.text((WIDTH // 2 - 50, 8), "amon-hen", fill=MUTED_GRAY, font=font_small)
    return img, draw


def render_full_screen(
    step: str = "init",
    query_text: str = "",
    open_cmd: str = "",
) -> Image.Image:
    img, draw = create_base_frame()
    x = 24
    y = 48

    # 1. Tolkien ASCII Art Header
    draw.text((x, y), "      /\\       ", fill=GOLD_ACCENT, font=font_bold)
    draw.text((x + 130, y), "A M O N   H E N", fill=GOLD_ACCENT, font=font_bold)
    draw.text((x + 280, y), "· The Seat of Seeing", fill=WHITE_TEXT, font=font_main)

    y += 20
    draw.text((x, y), "     /  \\      ", fill=GOLD_ACCENT, font=font_bold)
    draw.text((x + 130, y), '"From the high seat, no moment remains hidden."', fill=MUTED_GRAY, font=font_main)

    y += 20
    draw.text((x, y), "    / /\\ \\     ", fill=GOLD_ACCENT, font=font_bold)
    draw.text((x + 130, y), "Local Video Retrieval Engine · MobileCLIP2 (CPU)", fill=CYAN_TIME, font=font_main)

    y += 20
    draw.text((x, y), "   /_/  \\_\\    ", fill=GOLD_ACCENT, font=font_bold)
    draw.text((x + 130, y), "[v0.1.0]  [sqlite-vec]  [indexed: 1 video (49 frames)]", fill=GREEN_ACCENT, font=font_main)

    y += 32
    draw.line([24, y, WIDTH - 24, y], fill=(45, 45, 52))
    y += 18

    # 2. Prompt & Query Input
    if step in ("init", "typing_q"):
        draw.text((x, y), "amon-hen > ", fill=PROMPT_VIOLET, font=font_bold)
        draw.text((x + 105, y), query_text, fill=WHITE_TEXT, font=font_main)
        # Cursor
        cx = x + 105 + int(draw.textlength(query_text, font=font_main))
        draw.rectangle([cx + 2, y + 2, cx + 10, y + 18], fill=WHITE_TEXT)
        return img

    draw.text((x, y), "amon-hen > ", fill=PROMPT_VIOLET, font=font_bold)
    draw.text((x + 105, y), "a person holding an umbrella", fill=WHITE_TEXT, font=font_main)
    y += 24

    if step == "searching":
        draw.text((x, y), "Searching moments in vector index... (18ms)", fill=MUTED_GRAY, font=font_main)
        return img

    draw.text((x, y), "Searching moments in vector index... (18ms)", fill=MUTED_GRAY, font=font_main)
    y += 26

    # 3. Results Tree (Claude Code style, crisp glyphs, smooth solid score bars)
    bar_x = 320

    # Item #1 (Expanded Active Item)
    draw.text((x, y), "┌─ #1  ", fill=TREE_LINE, font=font_main)
    draw.text((x + 56, y), "00:00:37.0 - 00:01:06.0  ", fill=CYAN_TIME, font=font_main)

    # Smooth solid score bar
    draw.rounded_rectangle([bar_x, y + 4, bar_x + 90, y + 14], radius=2, fill=BAR_EMPTY)
    draw.rounded_rectangle([bar_x, y + 4, bar_x + 68, y + 14], radius=2, fill=GOLD_ACCENT)
    draw.text((bar_x + 105, y), "0.261", fill=GREEN_ACCENT, font=font_bold)

    y += 20
    draw.text((x, y), "│  File: cctv-people-demo.webm  │  Peak: 00:00:48.0 (high confidence)", fill=MUTED_GRAY, font=font_main)

    y += 20
    draw.text((x, y), "│  > Action: Type /open 1 to launch video at this timestamp", fill=GREEN_ACCENT, font=font_main)

    y += 20
    draw.text((x, y), "│", fill=TREE_LINE, font=font_main)

    # Item #2
    y += 18
    draw.text((x, y), "├─ #2  ", fill=TREE_LINE, font=font_main)
    draw.text((x + 56, y), "00:00:04.0 - 00:00:19.0  ", fill=CYAN_TIME, font=font_main)
    draw.rounded_rectangle([bar_x, y + 4, bar_x + 90, y + 14], radius=2, fill=BAR_EMPTY)
    draw.rounded_rectangle([bar_x, y + 4, bar_x + 64, y + 14], radius=2, fill=GOLD_ACCENT)
    draw.text((bar_x + 105, y), "0.247  cctv-people-demo.webm", fill=MUTED_GRAY, font=font_main)

    y += 20
    draw.text((x, y), "│", fill=TREE_LINE, font=font_main)

    # Item #3
    y += 18
    draw.text((x, y), "└─ #3  ", fill=TREE_LINE, font=font_main)
    draw.text((x + 56, y), "00:00:24.0 - 00:00:32.0  ", fill=CYAN_TIME, font=font_main)
    draw.rounded_rectangle([bar_x, y + 4, bar_x + 90, y + 14], radius=2, fill=BAR_EMPTY)
    draw.rounded_rectangle([bar_x, y + 4, bar_x + 58, y + 14], radius=2, fill=GOLD_ACCENT)
    draw.text((bar_x + 105, y), "0.227  cctv-people-demo.webm", fill=MUTED_GRAY, font=font_main)

    y += 30

    # 4. Next Prompt Action (/open 1)
    if step in ("results", "typing_open"):
        draw.text((x, y), "amon-hen > ", fill=PROMPT_VIOLET, font=font_bold)
        draw.text((x + 105, y), open_cmd, fill=WHITE_TEXT, font=font_main)
        cx = x + 105 + int(draw.textlength(open_cmd, font=font_main))
        draw.rectangle([cx + 2, y + 2, cx + 10, y + 18], fill=WHITE_TEXT)
        return img

    draw.text((x, y), "amon-hen > ", fill=PROMPT_VIOLET, font=font_bold)
    draw.text((x + 105, y), "/open 1", fill=WHITE_TEXT, font=font_main)
    y += 22

    draw.text((x, y), "=> Launching media player at 00:00:48.0 (cctv-people-demo.webm)...", fill=GREEN_ACCENT, font=font_main)
    y += 28

    # 5. Exit
    if step == "typing_exit":
        draw.text((x, y), "amon-hen > ", fill=PROMPT_VIOLET, font=font_bold)
        draw.text((x + 105, y), "/exit", fill=WHITE_TEXT, font=font_main)
        y += 22
        draw.text((x, y), "Farewell.", fill=MUTED_GRAY, font=font_main)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    # 1. Initial Launch with Tolkien ASCII Header
    frames.append(render_full_screen(step="init"))
    durations.append(900)

    # 2. Type Query
    q = "a person holding an umbrella"
    for i in range(1, len(q) + 1, 2):
        frames.append(render_full_screen(step="typing_q", query_text=q[:i]))
        durations.append(40)
    frames.append(render_full_screen(step="typing_q", query_text=q))
    durations.append(300)

    # 3. Searching Status
    frames.append(render_full_screen(step="searching"))
    durations.append(600)

    # 4. Display Results Tree
    frames.append(render_full_screen(step="results"))
    durations.append(1800)

    # 5. Type /open 1
    op = "/open 1"
    for i in range(1, len(op) + 1, 2):
        frames.append(render_full_screen(step="typing_open", open_cmd=op[:i]))
        durations.append(45)
    frames.append(render_full_screen(step="typing_open", open_cmd=op))
    durations.append(300)

    # 6. Player Launch Confirmation
    frames.append(render_full_screen(step="launched"))
    durations.append(1800)

    # 7. Exit
    frames.append(render_full_screen(step="typing_exit"))
    durations.append(3000)

    for path_name in ["demo/demo-tui-v7.gif", "demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Successfully generated perfect Tolkien Claude Code CLI demo ({len(frames)} frames, {Path('demo/demo-tui-v7.gif').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
