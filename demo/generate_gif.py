"""Render professional, clean, pixel-perfect TUI demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 920
HEIGHT = 600
BG_COLOR = (24, 25, 38)          # Obsidian dark
TITLE_BG = (18, 19, 28)          # Window titlebar
BORDER_COLOR = (50, 52, 70)
PANEL_BG = (30, 32, 46)          # Card background
PANEL_BORDER = (55, 58, 80)
HIGHLIGHT_BG = (38, 42, 64)
GOLD_ACCENT = (241, 218, 140)
GREEN_ACCENT = (80, 250, 123)
CYAN_ACCENT = (139, 233, 253)
WHITE_TEXT = (248, 248, 242)
MUTED_TEXT = (130, 138, 165)
PROGRESS_EMPTY = (40, 42, 58)

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font_main = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_header = ImageFont.truetype(FONT_BOLD_PATH, 17)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font_main = font_bold = font_header = font_small = ImageFont.load_default()


def draw_window_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Titlebar
    draw.rectangle([0, 0, WIDTH, 34], fill=TITLE_BG)
    draw.line([0, 34, WIDTH, 34], fill=BORDER_COLOR)

    # macOS window controls
    draw.ellipse([14, 11, 24, 21], fill=(255, 95, 86))
    draw.ellipse([30, 11, 40, 21], fill=(255, 189, 46))
    draw.ellipse([46, 11, 56, 21], fill=(39, 201, 63))

    # Window title
    draw.text((WIDTH // 2 - 85, 9), "Amon Hen — Seat of Seeing [TUI]", fill=MUTED_TEXT, font=font_small)

    # Outer border
    draw.rectangle([10, 42, WIDTH - 10, HEIGHT - 10], outline=BORDER_COLOR, width=1)

    return img, draw


def draw_clean_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    progress: float,
    color: tuple[int, int, int] = GOLD_ACCENT,
) -> None:
    """Draw a clean, modern rounded progress bar with smooth vector fill."""
    # Background track
    draw.rounded_rectangle([x, y, x + w, y + h], radius=3, fill=PROGRESS_EMPTY, outline=BORDER_COLOR)
    # Filled bar
    fill_w = max(0, min(w, int(w * progress)))
    if fill_w > 4:
        draw.rounded_rectangle([x, y, x + fill_w, y + h], radius=3, fill=color)


def render_tui_frame(
    prompt_input: str = "",
    results: list[dict] | None = None,
    indexing_state: tuple[str, float, str] | None = None,
    status_verb: str = "surveying",
    selected_rank: int | None = None,
    flash_message: str | None = None,
) -> Image.Image:
    img, draw = draw_window_frame()

    # --- Header Banner Panel ---
    draw.rectangle([12, 44, WIDTH - 12, 130], fill=PANEL_BG)
    draw.line([12, 130, WIDTH - 12, 130], fill=BORDER_COLOR)

    banner_text = "  A M O N   H E N  "
    tagline_text = '"From the Seat of Seeing, no moment remains hidden."'
    meta_text = "MobileCLIP2-S2  |  sqlite-vec  |  1 video indexed (49 frames)  |  CPU Mode"

    draw.text((WIDTH // 2 - 95, 54), banner_text, fill=GOLD_ACCENT, font=font_header)
    draw.text((WIDTH // 2 - 215, 80), tagline_text, fill=MUTED_TEXT, font=font_main)
    draw.text((WIDTH // 2 - 260, 104), meta_text, fill=CYAN_ACCENT, font=font_small)

    y_pos = 144

    # --- Indexing Progress Banner (if active) ---
    if indexing_state:
        vid_name, pct, spd = indexing_state
        draw.rectangle([20, y_pos, WIDTH - 20, y_pos + 68], fill=PANEL_BG, outline=BORDER_COLOR)
        draw.text((32, y_pos + 8), f"Indexing: {vid_name}", fill=WHITE_TEXT, font=font_bold)
        draw.text((WIDTH - 180, y_pos + 8), spd, fill=GREEN_ACCENT, font=font_bold)

        # Progress bar
        bar_x = 32
        bar_w = WIDTH - 64
        bar_y = y_pos + 36
        draw_clean_progress_bar(draw, bar_x, bar_y, bar_w, 14, pct, color=GREEN_ACCENT)
        draw.text((WIDTH // 2 - 15, bar_y - 1), f"{int(pct*100)}%", fill=WHITE_TEXT, font=font_small)
        y_pos += 80

    # --- Results Section ---
    if results:
        draw.text((24, y_pos), "RETRIEVED MOMENTS:", fill=GOLD_ACCENT, font=font_bold)
        draw.text((WIDTH - 300, y_pos), "SCORE BAR         CONFIDENCE", fill=MUTED_TEXT, font=font_small)
        y_pos += 24

        for idx, res in enumerate(results, start=1):
            is_active = (selected_rank == idx)
            card_bg = HIGHLIGHT_BG if is_active else PANEL_BG
            card_border = GOLD_ACCENT if is_active else PANEL_BORDER

            card_y = y_pos
            draw.rounded_rectangle([20, card_y, WIDTH - 20, card_y + 56], radius=4, fill=card_bg, outline=card_border, width=2 if is_active else 1)

            # Rank Badge
            rank_str = f"#{idx}"
            draw.text((36, card_y + 16), rank_str, fill=GOLD_ACCENT if is_active else MUTED_TEXT, font=font_header)

            # Time Interval & Video Info
            time_str = f"{res['start']}  ->  {res['end']}"
            draw.text((85, card_y + 10), time_str, fill=CYAN_ACCENT, font=font_bold)
            draw.text((85, card_y + 32), f"File: {res['file']}   Peak: {res['peak']}", fill=MUTED_TEXT, font=font_small)

            # Clean Graphic Score Bar
            bar_x = WIDTH - 300
            bar_y = card_y + 20
            score_val = res["score"]
            draw_clean_progress_bar(draw, bar_x, bar_y, 140, 14, score_val / 0.35, color=GOLD_ACCENT)

            # Score Number
            draw.text((WIDTH - 140, card_y + 17), f"{score_val:.3f}", fill=GREEN_ACCENT, font=font_bold)

            if is_active:
                draw.text((WIDTH - 80, card_y + 17), "PLAY", fill=GREEN_ACCENT, font=font_small)

            y_pos += 66

    # --- Flash Notification ---
    if flash_message:
        draw.rounded_rectangle([20, HEIGHT - 96, WIDTH - 20, HEIGHT - 64], radius=4, fill=(28, 55, 40), outline=GREEN_ACCENT)
        draw.text((34, HEIGHT - 87), f">> {flash_message}", fill=GREEN_ACCENT, font=font_main)

    # --- Bottom Prompt Bar ---
    prompt_y = HEIGHT - 52
    draw.rectangle([12, prompt_y, WIDTH - 12, HEIGHT - 12], fill=PANEL_BG)
    draw.line([12, prompt_y, WIDTH - 12, prompt_y], fill=BORDER_COLOR)

    # Prompt prompt_toolkit style
    prompt_str = "amon-hen > "
    draw.text((24, prompt_y + 8), prompt_str, fill=(189, 147, 249), font=font_bold)
    prefix_w = int(draw.textlength(prompt_str, font=font_bold))

    draw.text((24 + prefix_w, prompt_y + 8), prompt_input, fill=WHITE_TEXT, font=font_main)

    # Cursor
    cursor_x = 24 + prefix_w + int(draw.textlength(prompt_input, font=font_main))
    draw.rectangle([cursor_x + 2, prompt_y + 9, cursor_x + 10, prompt_y + 27], fill=WHITE_TEXT)

    # Status Right
    status_str = f"* {status_verb} | /help"
    draw.text((WIDTH - 180, prompt_y + 10), status_str, fill=MUTED_TEXT, font=font_small)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    res1 = [
        {"start": "00:00:37.0", "end": "00:01:06.0", "file": "cctv-people-demo.webm", "peak": "00:00:48.0", "score": 0.261},
        {"start": "00:00:04.0", "end": "00:00:19.0", "file": "cctv-people-demo.webm", "peak": "00:00:11.0", "score": 0.247},
        {"start": "00:00:24.0", "end": "00:00:32.0", "file": "cctv-people-demo.webm", "peak": "00:00:28.0", "score": 0.227},
    ]

    # Scene 1: Initial Screen
    frames.append(render_tui_frame(prompt_input="", status_verb="ready"))
    durations.append(900)

    # Scene 2: Indexing Progress
    for p in [0.20, 0.50, 0.85, 1.0]:
        frames.append(render_tui_frame(
            prompt_input="/index demo/",
            indexing_state=("cctv-people-demo.webm", p, "18.5x Realtime"),
            status_verb="discerning",
        ))
        durations.append(350)

    # Scene 3: Typing Search Query
    q1 = "a person holding an umbrella"
    for i in range(1, len(q1) + 1, 2):
        frames.append(render_tui_frame(prompt_input=q1[:i], status_verb="seeking"))
        durations.append(45)

    # Scene 4: Searching Animation
    for verb in ["surveying", "discerning", "unveiling"]:
        frames.append(render_tui_frame(prompt_input=q1, status_verb=verb))
        durations.append(180)

    # Scene 5: Displaying Search Results Cards
    frames.append(render_tui_frame(prompt_input="", results=res1, status_verb="gazing"))
    durations.append(1800)

    # Scene 6: Selecting Result #1
    for cmd in ["/o", "/open", "/open 1"]:
        frames.append(render_tui_frame(prompt_input=cmd, results=res1, selected_rank=1, status_verb="perceiving"))
        durations.append(250)

    # Scene 7: Video Launch Notification
    frames.append(render_tui_frame(
        prompt_input="",
        results=res1,
        selected_rank=1,
        flash_message="Launching VLC media player at 00:00:48.0 (cctv-people-demo.webm)...",
        status_verb="unveiled",
    ))
    durations.append(3000)

    # Save to demo/demo-tui.gif and demo/demo.gif
    for path_name in ["demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Successfully generated clean TUI demo ({len(frames)} frames, {Path('demo/demo-tui.gif').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
