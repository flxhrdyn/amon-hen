"""Render high-fidelity terminal demo GIF showcasing the Amon Hen interactive TUI REPL."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 860
HEIGHT = 560
BG_COLOR = (40, 42, 54)        # Dracula dark background
TITLE_BG = (33, 34, 44)        # Window header
BORDER_COLOR = (68, 71, 90)

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
if FONT_PATH:
    font = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 15) if os.path.exists("C:/Windows/Fonts/consolab.ttf") else font
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font = font_bold = font_small = ImageFont.load_default()


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
    draw.text((WIDTH // 2 - 60, 8), "amon-hen — interactive", fill=(140, 140, 150), font=font_small)
    return img


def render_state(lines: list[list[tuple[str, tuple[int, int, int]]]]) -> Image.Image:
    img = create_base_frame()
    draw = ImageDraw.Draw(img)
    x_start = 24
    y = 46
    line_height = 21

    for line in lines:
        x = x_start
        for chunk, color in line:
            draw.text((x, y), chunk, fill=color, font=font)
            x += int(draw.textlength(chunk, font=font))
        y += line_height

    return img


def main() -> None:
    # Colors
    sh_prompt_col = (80, 250, 123)   # Green ($ prompt)
    tui_prompt_col = (189, 147, 249) # Purple (amon-hen> prompt)
    cmd_col = (248, 248, 242)        # White
    muted_col = (98, 114, 164)       # Slate / Stone gray
    gold_col = (241, 250, 140)       # Muted Gold
    cyan_col = (139, 233, 253)       # Pale Blue
    success_col = (80, 250, 123)     # Moss Green

    frames: list[Image.Image] = []
    durations: list[int] = []

    seq = [
        ("prompt", "$ ", sh_prompt_col),
        ("type", "amon-hen", cmd_col),
        ("output", [
            [("  A M O N   H E N", gold_col)],
            [('  "From the Seat of Seeing, no moment remains hidden."', muted_col)],
            [("  v0.1.0 | model: mobileclip2-s2 | indexed: 1 video(s)", cyan_col)],
            [],
            [("Type your search query, /open <num> to launch video, or /help.", muted_col)],
            [],
        ]),
        ("pause", 700),
        ("prompt", "amon-hen> ", tui_prompt_col),
        ("type", "a person holding an umbrella", cmd_col),
        ("output", [
            [(" 1. ", muted_col), ("00:00:37.0 - 00:01:06.0  ", cyan_col), ("████████░░ ", gold_col), ("0.261  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [(" 2. ", muted_col), ("00:00:04.0 - 00:00:19.0  ", cyan_col), ("███████░░░ ", gold_col), ("0.247  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [(" 3. ", muted_col), ("00:00:24.0 - 00:00:32.0  ", cyan_col), ("██████░░░░ ", gold_col), ("0.227  ", success_col), ("cctv-people-demo.webm", cmd_col)],
            [],
        ]),
        ("pause", 1800),
        ("prompt", "amon-hen> ", tui_prompt_col),
        ("type", "/open 1", cmd_col),
        ("output", [
            [("Opening cctv-people-demo.webm at 00:37.0 in media player...", success_col)],
            [],
        ]),
        ("pause", 1400),
        ("prompt", "amon-hen> ", tui_prompt_col),
        ("type", "/exit", cmd_col),
        ("output", [
            [("Farewell.", muted_col)],
        ]),
        ("pause", 3500),
    ]

    current_lines: list[list[tuple[str, tuple[int, int, int]]]] = []
    for action, val, *extra in seq:
        if action == "prompt":
            p_col = extra[0] if extra else sh_prompt_col
            current_lines.append([(str(val), p_col)])
            frames.append(render_state(current_lines))
            durations.append(400)
        elif action == "type":
            cmd_text = str(val)
            c_col = extra[0] if extra else cmd_col
            for i in range(1, len(cmd_text) + 1, 2):
                partial = cmd_text[:i]
                temp_lines = [list(line) for line in current_lines[:-1]]
                temp_lines.append([(current_lines[-1][0][0], current_lines[-1][0][1]), (partial, c_col)])
                frames.append(render_state(temp_lines))
                durations.append(45)
            current_lines[-1].append((cmd_text, c_col))
            frames.append(render_state(current_lines))
            durations.append(250)
        elif action == "output":
            for out_line in val:
                current_lines.append(out_line)
            frames.append(render_state(current_lines))
            durations.append(500)
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
