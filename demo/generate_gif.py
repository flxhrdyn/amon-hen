"""Render 100% authentic Claude Code & Antigravity CLI demo with iconic Seeing Eye pixel art logo."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 560

# Dark Palette
BG_COLOR = (24, 24, 27)          # Dark background
TITLE_BG = (18, 18, 20)          # Titlebar
BORDER_COLOR = (45, 45, 52)      # Divider line
PROMPT_BORDER = (55, 57, 72)     # Horizontal divider above prompt

TEXT_WHITE = (244, 244, 245)     # Primary text
TEXT_SUB = (160, 165, 180)       # Subtitle text
TEXT_MUTED = (113, 113, 122)     # Gray metadata / footer
TEXT_CYAN = (56, 189, 248)       # Timestamp blue
TEXT_GREEN = (74, 222, 128)      # Score green
TEXT_GOLD = (250, 204, 21)       # Gold highlight

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font_main = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font_main = font_bold = font_small = ImageFont.load_default()

# Iconic "Eye of Seeing" Pixel Art Logo (Amon Hen)
EYE_GRID = [
    "    ████    ",
    "  ████████  ",
    " ███    ███ ",
    "████ ██ ████",
    "████ ██ ████",
    " ███    ███ ",
    "  ████████  ",
    "    ████    ",
    "   ██  ██   ",
    "  ██    ██  ",
]
COLOR_PALETTE = [
    (249, 226, 175), # Gold brow
    (250, 179, 135), # Amber
    (243, 139, 168), # Rose
    (203, 166, 247), # Violet iris
    (203, 166, 247), # Violet iris
    (137, 220, 235), # Starlight cyan
    (116, 199, 236), # Sky blue
    (137, 180, 250), # Deep blue
    (180, 190, 254), # Pedestal
    (180, 190, 254), # Pedestal
]


def create_base_screen() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Window titlebar
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COLOR)

    # macOS window controls
    draw.ellipse([14, 10, 24, 20], fill=(239, 68, 68))
    draw.ellipse([30, 10, 40, 20], fill=(245, 158, 11))
    draw.ellipse([46, 10, 56, 20], fill=(34, 197, 94))
    draw.text((WIDTH // 2 - 50, 8), "amon-hen", fill=TEXT_MUTED, font=font_small)

    # 1. Seeing Eye Pixel Art Logo
    x_art = 28
    y_art = 46
    pixel_size = 5

    for row_idx, row in enumerate(EYE_GRID):
        col = COLOR_PALETTE[row_idx]
        for col_idx, char in enumerate(row):
            if char != " ":
                px = x_art + col_idx * pixel_size
                py = y_art + row_idx * pixel_size
                draw.rectangle([px, py, px + pixel_size - 1, py + pixel_size - 1], fill=col)

    x_meta = x_art + 78
    draw.text((x_meta, y_art), "Amon Hen v0.1.0", fill=TEXT_WHITE, font=font_bold)
    draw.text((x_meta, y_art + 19), "The Seat of Seeing  ·  Local Video Retrieval Engine", fill=TEXT_SUB, font=font_main)
    draw.text((x_meta, y_art + 38), "MobileCLIP2-S2 (CPU)  ·  sqlite-vec (1 video, 49 frames)", fill=TEXT_MUTED, font=font_main)
    draw.text((x_meta, y_art + 57), "~/videos/cctv-people-demo.webm", fill=TEXT_MUTED, font=font_small)

    return img, draw


def render_screen(
    stream_content: list[tuple[str, tuple[int, int, int]]] | None = None,
    prompt_text: str = "",
    show_cursor: bool = True,
    footer_right: str = "MobileCLIP2 · CPU",
) -> Image.Image:
    img, draw = create_base_screen()

    # Stream Content Area
    y_stream = 142
    if stream_content:
        for line_text, col in stream_content:
            draw.text((28, y_stream), line_text, fill=col, font=font_main)
            y_stream += 23

    # Bottom Pinned Interactive Input Box (Claude Code / Antigravity Style)
    prompt_y = HEIGHT - 74
    draw.line([0, prompt_y, WIDTH, prompt_y], fill=PROMPT_BORDER)

    # > Prompt
    draw.text((28, prompt_y + 12), "> ", fill=TEXT_SUB, font=font_bold)
    draw.text((46, prompt_y + 12), prompt_text, fill=TEXT_WHITE, font=font_main)

    if show_cursor:
        cx = 46 + int(draw.textlength(prompt_text, font=font_main))
        draw.rectangle([cx + 2, prompt_y + 13, cx + 10, prompt_y + 29], fill=TEXT_WHITE)

    # Bottom Footer Status Bar
    footer_y = HEIGHT - 26
    draw.text((28, footer_y), "? for shortcuts · /open <id> to play · /exit", fill=TEXT_MUTED, font=font_small)
    draw.text((WIDTH - 180, footer_y), footer_right, fill=TEXT_MUTED, font=font_small)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    # Stream sequence - 100% Pure ASCII characters (0 broken font glyphs)
    results_stream = [
        ("> a person holding an umbrella", TEXT_WHITE),
        ("Searching moments in vector index... (18ms)", TEXT_MUTED),
        ("", TEXT_MUTED),
        (" 1. 00:00:37.0 - 00:01:06.0  [========  ] 0.261  cctv-people-demo.webm", TEXT_GREEN),
        ("    Peak: 00:00:48.0  ·  high confidence (type /open 1 to play)", TEXT_MUTED),
        ("", TEXT_MUTED),
        (" 2. 00:00:04.0 - 00:00:19.0  [=======   ] 0.247  cctv-people-demo.webm", TEXT_CYAN),
        (" 3. 00:00:24.0 - 00:00:32.0  [======    ] 0.227  cctv-people-demo.webm", TEXT_CYAN),
    ]

    open_stream = list(results_stream) + [
        ("", TEXT_MUTED),
        ("> /open 1", TEXT_WHITE),
        ("=> Launching media player at 00:00:48.0 (cctv-people-demo.webm)", TEXT_GREEN),
    ]

    # Scene 1: Initial Launch
    frames.append(render_screen(prompt_text="", show_cursor=True))
    durations.append(900)

    # Scene 2: Type Search Query
    q = "a person holding an umbrella"
    for i in range(1, len(q) + 1, 2):
        frames.append(render_screen(prompt_text=q[:i], show_cursor=True))
        durations.append(40)
    frames.append(render_screen(prompt_text=q, show_cursor=True))
    durations.append(300)

    # Scene 3: Searching
    frames.append(render_screen(
        stream_content=[
            ("> a person holding an umbrella", TEXT_WHITE),
            ("Searching moments in vector index... (18ms)", TEXT_MUTED),
        ],
        prompt_text="",
        show_cursor=True,
    ))
    durations.append(500)

    # Scene 4: Stream Results
    frames.append(render_screen(stream_content=results_stream, prompt_text="", show_cursor=True))
    durations.append(1800)

    # Scene 5: Type /open 1
    op = "/open 1"
    for i in range(1, len(op) + 1, 2):
        frames.append(render_screen(stream_content=results_stream, prompt_text=op[:i], show_cursor=True))
        durations.append(45)
    frames.append(render_screen(stream_content=results_stream, prompt_text=op, show_cursor=True))
    durations.append(300)

    # Scene 6: Video Player Launched
    frames.append(render_screen(stream_content=open_stream, prompt_text="", show_cursor=True))
    durations.append(2500)

    for path_name in ["demo/demo-tui-v9.gif", "demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Successfully generated Seeing Eye Antigravity demo ({len(frames)} frames, {Path('demo/demo-tui-v9.gif').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
