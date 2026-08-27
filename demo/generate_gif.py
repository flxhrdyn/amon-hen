"""Render authentic, elegant Tolkien-themed terminal demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 880
HEIGHT = 520

# Elegant Obsidian & Mithril Palette
BG_COLOR = (28, 29, 36)          # Deep obsidian stone
TITLE_BG = (20, 21, 26)          # Dark header
BORDER_COLOR = (50, 53, 66)

GOLD_TITLE = (229, 192, 123)     # Muted gold
STONE_GRAY = (130, 137, 151)     # Stone gray
STARLIGHT_BLUE = (97, 175, 239)  # Starlight pale blue
MOSS_GREEN = (152, 195, 121)     # Elven moss green
PROMPT_COLOR = (198, 120, 221)   # Mithril violet
WHITE_TEXT = (240, 240, 245)     # Clean text
BOX_BORDER = (75, 82, 99)        # Subtle box line

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font = font_bold = font_small = ImageFont.load_default()


def create_base_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Window titlebar
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COLOR)

    # macOS window controls
    draw.ellipse([14, 10, 24, 20], fill=(235, 95, 86))
    draw.ellipse([30, 10, 40, 20], fill=(235, 185, 50))
    draw.ellipse([46, 10, 56, 20], fill=(55, 195, 85))

    draw.text((WIDTH // 2 - 50, 8), "amon-hen", fill=STONE_GRAY, font=font_small)
    return img, draw


def render_terminal(lines: list[list[tuple[str, tuple[int, int, int]]]]) -> Image.Image:
    img, draw = create_base_frame()
    x_start = 24
    y = 48
    line_height = 22

    for line in lines:
        x = x_start
        for text, color in line:
            draw.text((x, y), text, fill=color, font=font)
            x += int(draw.textlength(text, font=font))
        y += line_height

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    header_box = [
        [("┌─────────────────────────────────────────────────────────────┐", BOX_BORDER)],
        [("│  ", BOX_BORDER), ("AMON HEN", GOLD_TITLE), ("  ·  The Seat of Seeing                            │", STONE_GRAY)],
        [("│  ", BOX_BORDER), ('"From the high seat, no moment remains hidden."            ', STONE_GRAY), ("│", BOX_BORDER)],
        [("│  ", BOX_BORDER), ("Local Video Engine · MobileCLIP2 (CPU) · 1 video (49 f)    ", STARLIGHT_BLUE), ("│", BOX_BORDER)],
        [("└─────────────────────────────────────────────────────────────┘", BOX_BORDER)],
        [],
    ]

    seq = [
        ("prompt", "$ ", MOSS_GREEN),
        ("type", "amon-hen", WHITE_TEXT),
        ("output", header_box),
        ("pause", 700),
        ("prompt", "amon-hen › ", PROMPT_COLOR),
        ("type", "a person holding an umbrella", WHITE_TEXT),
        ("output", [
            [(" 1. ", STONE_GRAY), ("00:00:37.0 - 00:01:06.0  ", STARLIGHT_BLUE), ("████████░░ ", GOLD_TITLE), ("0.261  ", MOSS_GREEN), ("cctv-demo.webm", WHITE_TEXT)],
            [(" 2. ", STONE_GRAY), ("00:00:04.0 - 00:00:19.0  ", STARLIGHT_BLUE), ("███████░░░ ", GOLD_TITLE), ("0.247  ", MOSS_GREEN), ("cctv-demo.webm", WHITE_TEXT)],
            [(" 3. ", STONE_GRAY), ("00:00:24.0 - 00:00:32.0  ", STARLIGHT_BLUE), ("██████░░░░ ", GOLD_TITLE), ("0.227  ", MOSS_GREEN), ("cctv-demo.webm", WHITE_TEXT)],
            [],
        ]),
        ("pause", 1800),
        ("prompt", "amon-hen › ", PROMPT_COLOR),
        ("type", "/open 1", WHITE_TEXT),
        ("output", [
            [("› Seeking moment at 00:00:37.0 in cctv-demo.webm (vlc)...", MOSS_GREEN)],
            [],
        ]),
        ("pause", 1400),
        ("prompt", "amon-hen › ", PROMPT_COLOR),
        ("type", "/exit", WHITE_TEXT),
        ("output", [
            [("› The seeing closes. Farewell.", STONE_GRAY)],
        ]),
        ("pause", 3500),
    ]

    current_lines: list[list[tuple[str, tuple[int, int, int]]]] = []
    for action, val, *extra in seq:
        if action == "prompt":
            col = extra[0] if extra else MOSS_GREEN
            current_lines.append([(str(val), col)])
            frames.append(render_terminal(current_lines))
            durations.append(400)
        elif action == "type":
            cmd = str(val)
            col = extra[0] if extra else WHITE_TEXT
            for i in range(1, len(cmd) + 1, 2):
                partial = cmd[:i]
                temp = [list(l) for l in current_lines[:-1]]
                temp.append([(current_lines[-1][0][0], current_lines[-1][0][1]), (partial, col)])
                frames.append(render_terminal(temp))
                durations.append(40)
            current_lines[-1].append((cmd, col))
            frames.append(render_terminal(current_lines))
            durations.append(250)
        elif action == "output":
            for line in val:
                current_lines.append(line)
            frames.append(render_terminal(current_lines))
            durations.append(450)
        elif action == "pause":
            frames.append(render_terminal(current_lines))
            durations.append(int(val))

    for path in ["demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Rendered refined Tolkien demo GIF: {len(frames)} frames, {Path('demo/demo-tui.gif').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
