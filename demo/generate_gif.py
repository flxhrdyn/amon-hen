"""Render high-fidelity terminal demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 840
HEIGHT = 440
BG_COLOR = (40, 42, 54)        # Dracula background
TITLE_BG = (33, 34, 44)        # Window header
BORDER_COLOR = (68, 71, 90)

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
if FONT_PATH:
    font = ImageFont.truetype(FONT_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font = font_small = ImageFont.load_default()


def create_base_frame() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title bar
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COLOR)

    # Window controls
    draw.ellipse([14, 10, 24, 20], fill=(255, 95, 86))   # Red
    draw.ellipse([30, 10, 40, 20], fill=(255, 189, 46))  # Yellow
    draw.ellipse([46, 10, 56, 20], fill=(39, 201, 63))   # Green

    # Window title
    draw.text((WIDTH // 2 - 40, 8), "amon-hen", fill=(140, 140, 150), font=font_small)
    return img


def render_state(lines: list[list[tuple[str, tuple[int, int, int]]]]) -> Image.Image:
    img = create_base_frame()
    draw = ImageDraw.Draw(img)
    x_start = 24
    y = 48
    line_height = 22

    for line in lines:
        x = x_start
        for chunk, color in line:
            draw.text((x, y), chunk, fill=color, font=font)
            x += int(draw.textlength(chunk, font=font))
        y += line_height

    return img


def main() -> None:
    # Colors
    prompt_col = (80, 250, 123)   # Green
    cmd_col = (248, 248, 242)     # White
    muted_col = (98, 114, 164)    # Slate / Gray
    gold_col = (241, 250, 140)    # Gold
    cyan_col = (139, 233, 253)    # Pale Blue
    success_col = (80, 250, 123)  # Green

    frames: list[Image.Image] = []
    durations: list[int] = []

    seq = [
        ("prompt", "$ "),
        ("type", "amon-hen index demo/ --sampler adaptive"),
        ("output", [
            [("Indexed 1 video(s), 49 frames in 2.7s", success_col)],
            [],
        ]),
        ("pause", 600),
        ("prompt", "$ "),
        ("type", 'amon-hen search "a person holding an umbrella"'),
        ("output", [
            [(" 1. ", muted_col), ("00:00:37.0 - 00:01:06.0  ", cyan_col), ("========== ", gold_col), ("0.261  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [(" 2. ", muted_col), ("00:00:04.0 - 00:00:19.0  ", cyan_col), ("=========  ", gold_col), ("0.247  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [(" 3. ", muted_col), ("00:00:24.0 - 00:00:32.0  ", cyan_col), ("========   ", gold_col), ("0.227  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [],
        ]),
        ("pause", 1500),
        ("prompt", "$ "),
        ("type", 'amon-hen search "a car passing by"'),
        ("output", [
            [(" 1. ", muted_col), ("00:00:24.0 - 00:00:32.0  ", cyan_col), ("========   ", gold_col), ("0.211  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [(" 2. ", muted_col), ("00:00:00.0 - 00:00:19.0  ", cyan_col), ("=======    ", gold_col), ("0.197  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [(" 3. ", muted_col), ("00:00:37.0 - 00:01:07.0  ", cyan_col), ("=======    ", gold_col), ("0.194  ", success_col), ("cctv-people-demo.webm", cmd_col)],
        ]),
        ("pause", 3500),
    ]

    current_lines: list[list[tuple[str, tuple[int, int, int]]]] = []
    for action, val in seq:
        if action == "prompt":
            current_lines.append([(val, prompt_col)])
            frames.append(render_state(current_lines))
            durations.append(400)
        elif action == "type":
            cmd_text = str(val)
            for i in range(1, len(cmd_text) + 1, 2):
                partial = cmd_text[:i]
                temp_lines = [list(line) for line in current_lines[:-1]]
                temp_lines.append([(current_lines[-1][0][0], prompt_col), (partial, cmd_col)])
                frames.append(render_state(temp_lines))
                durations.append(50)
            current_lines[-1].append((cmd_text, cmd_col))
            frames.append(render_state(current_lines))
            durations.append(300)
        elif action == "output":
            for out_line in val:
                current_lines.append(out_line)
            frames.append(render_state(current_lines))
            durations.append(600)
        elif action == "pause":
            frames.append(render_state(current_lines))
            durations.append(int(val))

    Path("demo").mkdir(exist_ok=True)
    out_path = Path("demo/demo.gif")
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Successfully generated {out_path} ({len(frames)} frames, {out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
