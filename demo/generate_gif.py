"""Render complete End-to-End demo GIF with ultra-clean Claude Code / AGY CLI layout (no heavy box cages)."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 580

# Pure CLI Standard Black Palette
BG_COLOR = (12, 12, 14)          # #0C0C0E Standard CLI black
TITLE_BG = (8, 8, 10)            # #08080A Titlebar
BORDER_COL = (38, 40, 50)        # #262832 Subtle divider line
ACTIVE_BG = (18, 24, 40)         # #121828 Subtle active row tint

# Single Accent Color: Starlight Blue
BLUE_PRIMARY = (130, 170, 255)   # #82AAFF
BAR_EMPTY = (32, 34, 44)         # #20222C Empty score track

# Monochrome Neutrals
TEXT_WHITE = (240, 243, 248)     # #F0F3F8 Pure White
TEXT_MUTED = (110, 115, 130)     # #6E7382 Gray metadata
TEXT_DIM = (75, 80, 95)          # #4B505F Dim line/legend

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font_main = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font_main = font_bold = font_small = ImageFont.load_default()

# Seat of Seeing at Amon Hen
THRONE_PIXELS = [
    " █     █     █ ",
    "███   ███   ███",
    "███   ███   ███",
    "███   ███   ███",
    "███   ███   ███",
    "████  ███  ████",
    "█████ ███ █████",
    "███████████████",
    " █████████████ ",
    "  ███████████  ",
    "███████████████",
]


def create_base_window() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Window titlebar
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COL)

    # Window controls
    draw.rectangle([14, 11, 22, 19], fill=(45, 48, 60))
    draw.rectangle([28, 11, 36, 19], fill=(45, 48, 60))
    draw.rectangle([42, 11, 50, 19], fill=BLUE_PRIMARY)
    draw.text((WIDTH // 2 - 50, 8), "amon-hen", fill=TEXT_MUTED, font=font_small)

    return img, draw


def render_shell_screen(lines: list[tuple[str, tuple[int, int, int]]]) -> Image.Image:
    """Render authentic shell terminal screen."""
    img, draw = create_base_window()
    x = 28
    y = 54
    line_h = 24
    for line_text, col in lines:
        draw.text((x, y), line_text, fill=col, font=font_main)
        y += line_h
    return img


def render_tui_screen(
    indexed_count: int = 0,
    indexing_state: tuple[str, float, str] | None = None,
    query_text: str = "",
    show_results: bool = False,
    selected_rank: int | None = None,
    notification_msg: str | None = None,
    input_text: str = "",
    show_cursor: bool = True,
) -> Image.Image:
    """Render ultra-clean Claude Code / AGY style TUI screen without heavy box cages."""
    img, draw = create_base_window()

    # 1. Header Section (Clean layout with subtle divider line)
    x_art = 28
    y_art = 48
    px_size = 5

    for r_idx, row in enumerate(THRONE_PIXELS):
        for c_idx, ch in enumerate(row):
            if ch != " ":
                px = x_art + c_idx * px_size
                py = y_art + r_idx * px_size
                draw.rectangle([px, py, px + px_size - 1, py + px_size - 1], fill=BLUE_PRIMARY)

    x_text = x_art + 90
    draw.text((x_text, 48), "Amon Hen v0.1.0", fill=BLUE_PRIMARY, font=font_bold)
    draw.text((x_text + 140, 49), '· "From the Seat of Seeing, no moment remains hidden."', fill=TEXT_WHITE, font=font_main)

    idx_str = f"Index: {indexed_count} video ({indexed_count * 49} frames)" if indexed_count > 0 else "Index: Ready (0 videos)"
    draw.text((x_text, 72), f"Model: MobileCLIP2-S0 (CPU)   Storage: sqlite-vec   {idx_str}", fill=TEXT_MUTED, font=font_small)
    draw.text((x_text, 89), "~/videos/demo/", fill=TEXT_MUTED, font=font_small)

    # Subtle horizontal divider below header
    draw.line([28, 116, WIDTH - 28, 116], fill=BORDER_COL)

    y_content = 132

    # 2. Live Indexing Section (Clean line + progress bar)
    if indexing_state:
        verb_label, pct, spd = indexing_state
        draw.text((28, y_content), f"* {verb_label}", fill=TEXT_WHITE, font=font_bold)
        draw.text((WIDTH - 180, y_content), spd, fill=BLUE_PRIMARY, font=font_bold)

        bar_w = WIDTH - 56
        draw.rectangle([28, y_content + 24, 28 + bar_w, y_content + 32], fill=BAR_EMPTY)
        fill_w = max(0, min(bar_w, int(bar_w * pct)))
        if fill_w > 0:
            draw.rectangle([28, y_content + 24, 28 + fill_w, y_content + 32], fill=BLUE_PRIMARY)
        y_content += 56

    # 3. Query Section (Natural inline prompt line, like Claude Code)
    if query_text:
        draw.text((28, y_content), f"> {query_text}", fill=TEXT_WHITE, font=font_bold)
        draw.text((WIDTH - 150, y_content), "Gazed in 18ms", fill=BLUE_PRIMARY, font=font_small)
        y_content += 32

    # 4. Results List (Clean indented moment list, no heavy box cages)
    if show_results:
        bar_x = WIDTH - 240

        # Item #1 (Active focused item with subtle left bar & blue accent)
        is_sel_1 = (selected_rank == 1)
        if is_sel_1:
            draw.rectangle([28, y_content - 4, WIDTH - 28, y_content + 64], fill=ACTIVE_BG)
            draw.rectangle([28, y_content - 4, 31, y_content + 64], fill=BLUE_PRIMARY)  # Left accent bar

        draw.text((38, y_content), "#1   00:00:37.0 -> 00:01:06.0", fill=BLUE_PRIMARY, font=font_bold)
        draw.text((38, y_content + 22), "File: cctv-people-demo.webm   Peak: 00:00:48.0", fill=TEXT_MUTED, font=font_small)
        draw.text((38, y_content + 42), "=> Action: Type /open 1 to play moment in VLC", fill=BLUE_PRIMARY, font=font_small)

        # Flat clean Blue score bar #1
        draw.rectangle([bar_x, y_content + 10, bar_x + 110, y_content + 20], fill=BAR_EMPTY)
        draw.rectangle([bar_x, y_content + 10, bar_x + 85, y_content + 20], fill=BLUE_PRIMARY)
        draw.text((bar_x + 125, y_content + 6), "0.261", fill=BLUE_PRIMARY, font=font_bold)
        y_content += 74

        # Item #2 (Clean White list item)
        draw.text((38, y_content), "#2   00:00:04.0 -> 00:00:19.0", fill=TEXT_WHITE, font=font_bold)
        draw.text((38, y_content + 22), "File: cctv-people-demo.webm   Peak: 00:00:11.0", fill=TEXT_MUTED, font=font_small)
        # Flat White score bar #2
        draw.rectangle([bar_x, y_content + 8, bar_x + 110, y_content + 18], fill=BAR_EMPTY)
        draw.rectangle([bar_x, y_content + 8, bar_x + 78, y_content + 18], fill=TEXT_WHITE)
        draw.text((bar_x + 125, y_content + 4), "0.247", fill=TEXT_WHITE, font=font_bold)
        y_content += 52

        # Item #3 (Clean White list item)
        draw.text((38, y_content), "#3   00:00:24.0 -> 00:00:32.0", fill=TEXT_WHITE, font=font_bold)
        draw.text((38, y_content + 22), "File: cctv-people-demo.webm   Peak: 00:00:28.0", fill=TEXT_MUTED, font=font_small)
        # Flat White score bar #3
        draw.rectangle([bar_x, y_content + 8, bar_x + 110, y_content + 18], fill=BAR_EMPTY)
        draw.rectangle([bar_x, y_content + 8, bar_x + 70, y_content + 18], fill=TEXT_WHITE)
        draw.text((bar_x + 125, y_content + 4), "0.227", fill=TEXT_WHITE, font=font_bold)
        y_content += 48

    # 5. Toast Notification (Clean inline message)
    if notification_msg:
        draw.text((28, 436), f"=> {notification_msg}", fill=BLUE_PRIMARY, font=font_main)

    # 6. Bottom Prompt Line (Exact Claude Code / AGY CLI Style: single top divider line + clean prompt)
    draw.line([28, 480, WIDTH - 28, 480], fill=BORDER_COL)  # Single top divider line like AGY

    draw.text((28, 498), "> ", fill=BLUE_PRIMARY, font=font_bold)
    draw.text((46, 498), input_text, fill=TEXT_WHITE, font=font_main)

    if show_cursor:
        cx = 46 + int(draw.textlength(input_text, font=font_main))
        draw.rectangle([cx + 2, 498, cx + 10, 514], fill=BLUE_PRIMARY)

    # Footer Metadata Line (below prompt, exactly like Claude Code / AGY)
    draw.text((28, 532), "[Enter] Submit  ·  /index <dir>  ·  /open <id>  ·  /exit", fill=TEXT_DIM, font=font_small)
    draw.text((WIDTH - 160, 532), "MobileCLIP2-S0 · CPU", fill=TEXT_DIM, font=font_small)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    # === SCENE 1: Launch TUI directly from Shell ===
    frames.append(render_shell_screen([
        ("PS C:\\Users\\Felix\\videos> ", BLUE_PRIMARY)
    ]))
    durations.append(400)

    launch_cmd = "amon-hen"
    for i in range(1, len(launch_cmd) + 1, 2):
        frames.append(render_shell_screen([
            (f"PS C:\\Users\\Felix\\videos> {launch_cmd[:i]}", TEXT_WHITE)
        ]))
        durations.append(40)

    # === SCENE 2: Inside TUI — Live Indexing with Genuine Progress ===
    frames.append(render_tui_screen(indexed_count=0, input_text="", show_cursor=True))
    durations.append(800)

    idx_cmd = "/index demo/"
    for i in range(1, len(idx_cmd) + 1, 2):
        frames.append(render_tui_screen(indexed_count=0, input_text=idx_cmd[:i], show_cursor=True))
        durations.append(40)
    frames.append(render_tui_screen(indexed_count=0, input_text=idx_cmd, show_cursor=True))
    durations.append(250)

    # Indexing Progress with turning verb "Gazing" and "Delving"
    frames.append(render_tui_screen(
        indexed_count=0,
        indexing_state=("Gazing across cctv-people-demo.webm", 0.35, "18.5x Realtime"),
        input_text="",
        show_cursor=True,
    ))
    durations.append(300)

    frames.append(render_tui_screen(
        indexed_count=0,
        indexing_state=("Delving keyframes with MobileCLIP2", 0.75, "18.5x Realtime"),
        input_text="",
        show_cursor=True,
    ))
    durations.append(300)

    frames.append(render_tui_screen(
        indexed_count=1,
        indexing_state=("Unveiled 49 moments into index database", 1.0, "Done (49 frames)"),
        input_text="",
        show_cursor=True,
    ))
    durations.append(700)

    # === SCENE 3: Search Querying & Instant 18ms Retrieval ===
    q = "a person holding an umbrella"
    for i in range(1, len(q) + 1, 2):
        frames.append(render_tui_screen(indexed_count=1, input_text=q[:i], show_cursor=True))
        durations.append(35)
    frames.append(render_tui_screen(indexed_count=1, input_text=q, show_cursor=True))
    durations.append(300)

    # Submit query -> Instant 18ms Results list!
    frames.append(render_tui_screen(
        indexed_count=1,
        query_text=q,
        show_results=True,
        input_text="",
        show_cursor=True,
    ))
    durations.append(2200)

    # === SCENE 4: Open video moment (/open 1) ===
    op = "/open 1"
    for i in range(1, len(op) + 1, 2):
        frames.append(render_tui_screen(
            indexed_count=1,
            query_text=q,
            show_results=True,
            selected_rank=1,
            input_text=op[:i],
            show_cursor=True,
        ))
        durations.append(40)
    frames.append(render_tui_screen(
        indexed_count=1,
        query_text=q,
        show_results=True,
        selected_rank=1,
        input_text=op,
        show_cursor=True,
    ))
    durations.append(250)

    # Submit -> Player Launch Toast
    frames.append(render_tui_screen(
        indexed_count=1,
        query_text=q,
        show_results=True,
        selected_rank=1,
        notification_msg="Launching media player at 00:00:48.0 (cctv-people-demo.webm)...",
        input_text="",
        show_cursor=True,
    ))
    durations.append(2400)

    # === SCENE 5: Exit TUI session ===
    ex = "/exit"
    for i in range(1, len(ex) + 1, 2):
        frames.append(render_tui_screen(
            indexed_count=1,
            query_text=q,
            show_results=True,
            selected_rank=1,
            notification_msg="Launching media player at 00:00:48.0 (cctv-people-demo.webm)...",
            input_text=ex[:i],
            show_cursor=True,
        ))
        durations.append(40)

    # Return to Shell
    frames.append(render_shell_screen([
        ("PS C:\\Users\\Felix\\videos> amon-hen", TEXT_WHITE),
        ("Farewell. The seeing closes.", BLUE_PRIMARY),
        ("", TEXT_MUTED),
        ("PS C:\\Users\\Felix\\videos> ", BLUE_PRIMARY),
    ]))
    durations.append(3000)

    out_path = Path("demo/demo.gif")
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Successfully generated ultra-clean demo ({len(frames)} frames, {out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
