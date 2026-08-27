"""Render a clean, authentic, professional terminal demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 860
HEIGHT = 480
BG_COLOR = (30, 30, 30)         # Clean dark neutral terminal
TITLE_BG = (42, 42, 42)         # Terminal window titlebar
BORDER_COLOR = (60, 60, 60)

# Colors - Modern clean syntax
COLOR_PROMPT = (100, 200, 100)   # Clean green
COLOR_TUI_PROMPT = (170, 140, 240) # Subtle purple
COLOR_TEXT = (235, 235, 235)     # Clean white
COLOR_MUTED = (140, 140, 140)    # Gray metadata
COLOR_TIME = (100, 180, 240)     # Blue timestamp
COLOR_SCORE = (130, 215, 130)    # Soft green score

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
if FONT_PATH:
    font = ImageFont.truetype(FONT_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font = font_small = ImageFont.load_default()


def create_base_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Window header
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COLOR)

    # Window controls
    draw.ellipse([14, 10, 24, 20], fill=(255, 95, 86))
    draw.ellipse([30, 10, 40, 20], fill=(255, 189, 46))
    draw.ellipse([46, 10, 56, 20], fill=(39, 201, 63))

    draw.text((WIDTH // 2 - 45, 8), "amon-hen", fill=COLOR_MUTED, font=font_small)
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

    seq = [
        ("prompt", "$ ", COLOR_PROMPT),
        ("type", "amon-hen index cctv-demo.webm --sampler adaptive", COLOR_TEXT),
        ("output", [
            [("Indexed 1 video(s), 49 frames in 2.7s (18.5x Realtime)", COLOR_SCORE)],
            [],
        ]),
        ("pause", 600),
        ("prompt", "$ ", COLOR_PROMPT),
        ("type", "amon-hen", COLOR_TEXT),
        ("output", [
            [("amon-hen v0.1.0 (mobileclip2-s2 | cpu)", COLOR_MUTED)],
            [("Database: ~/.amonhen/index.db (1 video, 49 frames)", COLOR_MUTED)],
            [],
            [("Type a query, /open <num>, or /exit.", COLOR_MUTED)],
            [],
        ]),
        ("pause", 700),
        ("prompt", "amon-hen> ", COLOR_TUI_PROMPT),
        ("type", "a person holding an umbrella", COLOR_TEXT),
        ("output", [
            [(" 1. ", COLOR_MUTED), ("00:00:37.0 - 00:01:06.0  ", COLOR_TIME), ("0.261  ", COLOR_SCORE), ("cctv-demo.webm", COLOR_TEXT)],
            [(" 2. ", COLOR_MUTED), ("00:00:04.0 - 00:00:19.0  ", COLOR_TIME), ("0.247  ", COLOR_SCORE), ("cctv-demo.webm", COLOR_TEXT)],
            [(" 3. ", COLOR_MUTED), ("00:00:24.0 - 00:00:32.0  ", COLOR_TIME), ("0.227  ", COLOR_SCORE), ("cctv-demo.webm", COLOR_TEXT)],
            [],
        ]),
        ("pause", 1600),
        ("prompt", "amon-hen> ", COLOR_TUI_PROMPT),
        ("type", "/open 1", COLOR_TEXT),
        ("output", [
            [("Opening cctv-demo.webm at 00:00:37.0 (vlc)...", COLOR_SCORE)],
            [],
        ]),
        ("pause", 1200),
        ("prompt", "amon-hen> ", COLOR_TUI_PROMPT),
        ("type", "/exit", COLOR_TEXT),
        ("output", [
            [],
        ]),
        ("pause", 3000),
    ]

    current_lines: list[list[tuple[str, tuple[int, int, int]]]] = []
    for action, val, *extra in seq:
        if action == "prompt":
            col = extra[0] if extra else COLOR_PROMPT
            current_lines.append([(str(val), col)])
            frames.append(render_terminal(current_lines))
            durations.append(400)
        elif action == "type":
            cmd = str(val)
            col = extra[0] if extra else COLOR_TEXT
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
            durations.append(500)
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
    print(f"Rendered clean GIF: {len(frames)} frames, {Path('demo/demo-tui.gif').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
