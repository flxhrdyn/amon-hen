"""Render authentic, high-fidelity TUI mockup demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 580
BG_COLOR = (24, 25, 38)          # Deep stone obsidian
TITLE_BG = (18, 19, 28)          # Window header
BORDER_COLOR = (54, 57, 75)
PANEL_BG = (30, 32, 48)          # Card/panel background
HEADER_BORDER = (90, 80, 120)

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font_main = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_header = ImageFont.truetype(FONT_BOLD_PATH, 17)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font_main = font_bold = font_header = font_small = ImageFont.load_default()

# Color Palette (Tolkien & Dracula Hybrid)
GOLD_TEXT = (241, 218, 140)
PURPLE_PROMPT = (189, 147, 249)
GREEN_TEXT = (80, 250, 123)
CYAN_TIME = (139, 233, 253)
WHITE_TEXT = (248, 248, 242)
MUTED_TEXT = (118, 128, 160)
STONE_BORDER = (68, 71, 90)
HIGHLIGHT_BG = (42, 45, 68)


def draw_window_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Window titlebar
    draw.rectangle([0, 0, WIDTH, 34], fill=TITLE_BG)
    draw.line([0, 34, WIDTH, 34], fill=BORDER_COLOR)

    # macOS window dots
    draw.ellipse([14, 11, 24, 21], fill=(255, 95, 86))
    draw.ellipse([30, 11, 40, 21], fill=(255, 189, 46))
    draw.ellipse([46, 11, 56, 21], fill=(39, 201, 63))

    # Window center title
    draw.text((WIDTH // 2 - 80, 9), "Amon Hen — Seat of Seeing [TUI]", fill=MUTED_TEXT, font=font_small)

    # Outer decorative border
    draw.rectangle([10, 44, WIDTH - 10, HEIGHT - 10], outline=STONE_BORDER, width=1)

    return img, draw


def render_tui_frame(
    prompt_input: str = "",
    results: list[dict] | None = None,
    indexing_progress: tuple[str, float, str] | None = None,
    status_bar_verb: str = "surveying",
    active_selection: int | None = None,
    notification: str | None = None,
) -> Image.Image:
    img, draw = draw_window_frame()

    # --- Top Banner Panel ---
    draw.rectangle([12, 46, WIDTH - 12, 130], fill=PANEL_BG)
    draw.line([12, 130, WIDTH - 12, 130], fill=STONE_BORDER)

    banner_art = "  ▲  A M O N   H E N  ▲  "
    tagline = '"From the Seat of Seeing, no moment remains hidden."'
    meta = "MobileCLIP2-S2  |  sqlite-vec  |  1 video indexed (49 frames)  |  CPU Mode"

    draw.text((WIDTH // 2 - 130, 56), banner_art, fill=GOLD_TEXT, font=font_header)
    draw.text((WIDTH // 2 - 210, 82), tagline, fill=MUTED_TEXT, font=font_main)
    draw.text((WIDTH // 2 - 255, 106), meta, fill=CYAN_TIME, font=font_small)

    # --- Main Content Area ---
    y_cursor = 146

    # Optional Indexing Progress Box
    if indexing_progress:
        vid_name, pct, spd = indexing_progress
        draw.rectangle([24, y_cursor, WIDTH - 24, y_cursor + 64], fill=PANEL_BG, outline=STONE_BORDER)
        draw.text((36, y_cursor + 8), f"Indexing: {vid_name}", fill=WHITE_TEXT, font=font_bold)
        draw.text((WIDTH - 160, y_cursor + 8), spd, fill=GREEN_TEXT, font=font_main)

        # Progress bar
        bar_x = 36
        bar_w = WIDTH - 72
        bar_y = y_cursor + 36
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 14], fill=(20, 20, 30), outline=STONE_BORDER)
        fill_w = int(bar_w * pct)
        if fill_w > 0:
            draw.rectangle([bar_x + 1, bar_y + 1, bar_x + fill_w, bar_y + 13], fill=GOLD_TEXT)
        draw.text((WIDTH // 2 - 15, bar_y - 2), f"{int(pct*100)}%", fill=BG_COLOR if fill_w > bar_w//2 else WHITE_TEXT, font=font_small)
        y_cursor += 76

    # Search Results Table / Cards
    if results:
        draw.text((28, y_cursor), "RETRIEVED MOMENTS:", fill=GOLD_TEXT, font=font_bold)
        draw.text((WIDTH - 240, y_cursor), "RANK   INTERVAL         SIMILARITY", fill=MUTED_TEXT, font=font_small)
        y_cursor += 24

        for idx, res in enumerate(results, start=1):
            is_active = (active_selection == idx)
            card_bg = HIGHLIGHT_BG if is_active else PANEL_BG
            border_col = GOLD_TEXT if is_active else STONE_BORDER

            card_y = y_cursor
            draw.rectangle([24, card_y, WIDTH - 24, card_y + 54], fill=card_bg, outline=border_col, width=2 if is_active else 1)

            # Left Badge (Rank)
            badge_text = f"#{idx}"
            draw.text((40, card_y + 16), badge_text, fill=GOLD_TEXT if is_active else MUTED_TEXT, font=font_header)

            # Middle Segment Interval & Video
            interval_str = f"{res['start']}  ➔  {res['end']}"
            draw.text((90, card_y + 10), interval_str, fill=CYAN_TIME, font=font_bold)
            draw.text((90, card_y + 30), f"File: {res['file']}  |  Peak: {res['peak']}", fill=MUTED_TEXT, font=font_small)

            # Right Visual Score Bar & Score
            score_bar = res["bar"]
            draw.text((WIDTH - 290, card_y + 16), score_bar, fill=GOLD_TEXT, font=font_main)
            draw.text((WIDTH - 120, card_y + 16), f"{res['score']:.3f}", fill=GREEN_TEXT, font=font_bold)

            if is_active:
                draw.text((WIDTH - 200, card_y + 36), "▶ Press ENTER to play", fill=GREEN_TEXT, font=font_small)

            y_cursor += 62

    # Bottom Notification / Flash Message
    if notification:
        draw.rectangle([24, HEIGHT - 92, WIDTH - 24, HEIGHT - 64], fill=(30, 60, 45), outline=GREEN_TEXT)
        draw.text((36, HEIGHT - 86), notification, fill=GREEN_TEXT, font=font_main)

    # --- Bottom Prompt Bar & Status Line ---
    prompt_y = HEIGHT - 52
    draw.rectangle([12, prompt_y, WIDTH - 12, HEIGHT - 12], fill=PANEL_BG)
    draw.line([12, prompt_y, WIDTH - 12, prompt_y], fill=STONE_BORDER)

    # Prompt text
    prompt_prefix = "amon-hen ❯ "
    draw.text((24, prompt_y + 8), prompt_prefix, fill=PURPLE_PROMPT, font=font_bold)
    prefix_w = int(draw.textlength(prompt_prefix, font=font_bold))

    draw.text((24 + prefix_w, prompt_y + 8), prompt_input, fill=WHITE_TEXT, font=font_main)

    # Cursor
    cursor_x = 24 + prefix_w + int(draw.textlength(prompt_input, font=font_main))
    draw.rectangle([cursor_x + 2, prompt_y + 10, cursor_x + 10, prompt_y + 26], fill=WHITE_TEXT)

    # Right Status indicator
    status_str = f"● {status_bar_verb} | /help"
    draw.text((WIDTH - 190, prompt_y + 10), status_str, fill=MUTED_TEXT, font=font_small)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    res1 = [
        {"start": "00:00:37.0", "end": "00:01:06.0", "file": "cctv-people-demo.webm", "peak": "00:00:48.0", "bar": "████████░░", "score": 0.261},
        {"start": "00:00:04.0", "end": "00:00:19.0", "file": "cctv-people-demo.webm", "peak": "00:00:11.0", "bar": "███████░░░", "score": 0.247},
        {"start": "00:00:24.0", "end": "00:00:32.0", "file": "cctv-people-demo.webm", "peak": "00:00:28.0", "bar": "██████░░░░", "score": 0.227},
    ]

    # Scene 1: Initial Launch
    frames.append(render_tui_frame(prompt_input="", status_bar_verb="waiting"))
    durations.append(800)

    # Scene 2: Indexing Progress
    for p in [0.25, 0.60, 0.90, 1.0]:
        frames.append(render_tui_frame(
            prompt_input="/index demo/",
            indexing_progress=("cctv-people-demo.webm", p, "18.5x Realtime"),
            status_bar_verb="discerning",
        ))
        durations.append(300)

    # Scene 3: Typing Query 1
    q1 = "a person holding an umbrella"
    for i in range(1, len(q1) + 1, 2):
        frames.append(render_tui_frame(prompt_input=q1[:i], status_bar_verb="seeking"))
        durations.append(50)

    # Scene 4: Searching Animation
    for verb in ["surveying", "discerning", "unveiling"]:
        frames.append(render_tui_frame(prompt_input=q1, status_bar_verb=verb))
        durations.append(150)

    # Scene 5: Displaying Search Results Cards
    frames.append(render_tui_frame(prompt_input="", results=res1, status_bar_verb="gazing"))
    durations.append(1500)

    # Scene 6: Selecting Result #1
    for cmd in ["/o", "/open", "/open 1"]:
        frames.append(render_tui_frame(prompt_input=cmd, results=res1, active_selection=1, status_bar_verb="perceiving"))
        durations.append(250)

    # Scene 7: Video Launch Notification Card
    frames.append(render_tui_frame(
        prompt_input="",
        results=res1,
        active_selection=1,
        notification="✓ Launching VLC at 00:00:48.0 (cctv-people-demo.webm)",
        status_bar_verb="unveiled",
    ))
    durations.append(2800)

    out_path = Path("demo/demo.gif")
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Successfully generated full TUI mockup demo at {out_path} ({len(frames)} frames, {out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
