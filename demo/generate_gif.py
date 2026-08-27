"""Render authentic Claude Code-inspired CLI demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 580

# Clean Dark Monokai/Claude Terminal Palette
BG_COLOR = (24, 24, 27)          # Deep zinc dark
TITLE_BG = (18, 18, 20)          # Clean window titlebar
BORDER_COLOR = (45, 45, 52)

PROMPT_VIOLET = (192, 132, 252)  # Claude Code violet/purple prompt
GOLD_ACCENT = (250, 204, 21)     # Muted gold
CYAN_TIME = (56, 189, 248)       # Starlight cyan
GREEN_ACCENT = (74, 222, 128)    # Clean success green
WHITE_TEXT = (244, 244, 245)     # Crisp zinc-100 text
MUTED_GRAY = (113, 113, 122)     # Muted zinc-500
TREE_LINE = (82, 82, 91)         # Tree lines (zinc-600)
TAG_BG = (39, 39, 42)            # Subtle inline pill/tag background

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


def render_terminal(lines: list[list[tuple[str, tuple[int, int, int]]]]) -> Image.Image:
    img, draw = create_base_frame()
    x_start = 24
    y = 48
    line_h = 22

    for line in lines:
        x = x_start
        for text, color in line:
            draw.text((x, y), text, fill=color, font=font_main)
            x += int(draw.textlength(text, font=font_main))
        y += line_h

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    # Claude Code style header (subtle logo, clean status line)
    claude_header = [
        [("╭─ ", TREE_LINE), ("amon-hen", GOLD_ACCENT), (" v0.1.0 · The Seat of Seeing", MUTED_GRAY)],
        [("│  ", TREE_LINE), ("model: ", MUTED_GRAY), ("mobileclip2-s2", CYAN_TIME), ("  storage: ", MUTED_GRAY), ("sqlite-vec (cpu)", GREEN_ACCENT), ("  index: ", MUTED_GRAY), ("1 video (49 frames)", WHITE_TEXT)],
        [("╰───────────────────────────────────────────────────────────", TREE_LINE)],
        [],
    ]

    # Indexing progress stream (Claude Code style tool/action call)
    indexing_stream = [
        [("╭─ ", TREE_LINE), ("amon-hen", GOLD_ACCENT), (" v0.1.0 · The Seat of Seeing", MUTED_GRAY)],
        [("│  ", TREE_LINE), ("model: ", MUTED_GRAY), ("mobileclip2-s2", CYAN_TIME), ("  storage: ", MUTED_GRAY), ("sqlite-vec (cpu)", GREEN_ACCENT), ("  index: ", MUTED_GRAY), ("1 video (49 frames)", WHITE_TEXT)],
        [("╰───────────────────────────────────────────────────────────", TREE_LINE)],
        [],
        [("amon-hen ❯ ", PROMPT_VIOLET), ("/index demo/", WHITE_TEXT)],
        [("  ● Indexing ", GOLD_ACCENT), ("cctv-people-demo.webm", WHITE_TEXT), (" [====================] 100% (18.5x RT)", GREEN_ACCENT)],
        [("  ✓ Indexed 1 video(s), 49 frames in 2.7s", GREEN_ACCENT)],
        [],
    ]

    # Clean Claude Code structured search result stream (Tree branches + inline confidence pills)
    results_stream = [
        [("╭─ ", TREE_LINE), ("amon-hen", GOLD_ACCENT), (" v0.1.0 · The Seat of Seeing", MUTED_GRAY)],
        [("│  ", TREE_LINE), ("model: ", MUTED_GRAY), ("mobileclip2-s2", CYAN_TIME), ("  storage: ", MUTED_GRAY), ("sqlite-vec (cpu)", GREEN_ACCENT), ("  index: ", MUTED_GRAY), ("1 video (49 frames)", WHITE_TEXT)],
        [("╰───────────────────────────────────────────────────────────", TREE_LINE)],
        [],
        [("amon-hen ❯ ", PROMPT_VIOLET), ("a person holding an umbrella", WHITE_TEXT)],
        [("  Searching moments in vector index... (18ms)", MUTED_GRAY)],
        [],
        [("  ┌─ ", TREE_LINE), ("#1  ", GOLD_ACCENT), ("00:00:37.0 - 00:01:06.0  ", CYAN_TIME), ("[████████░░] 0.261", GREEN_ACCENT)],
        [("  │  ", TREE_LINE), ("File: ", MUTED_GRAY), ("cctv-people-demo.webm", WHITE_TEXT), ("  │  Peak: ", MUTED_GRAY), ("00:00:48.0", CYAN_TIME), (" (high confidence)", MUTED_GRAY)],
        [("  │  ", TREE_LINE), ("▶ Action: Type ", MUTED_GRAY), ("/open 1", PROMPT_VIOLET), (" to launch video at this timestamp", MUTED_GRAY)],
        [("  │", TREE_LINE)],
        [("  ├─ ", TREE_LINE), ("#2  ", MUTED_GRAY), ("00:00:04.0 - 00:00:19.0  ", CYAN_TIME), ("[███████░░░] 0.247", GREEN_ACCENT), ("  cctv-people-demo.webm", MUTED_GRAY)],
        [("  │", TREE_LINE)],
        [("  └─ ", TREE_LINE), ("#3  ", MUTED_GRAY), ("00:00:24.0 - 00:00:32.0  ", CYAN_TIME), ("[██████░░░░] 0.227", GREEN_ACCENT), ("  cctv-people-demo.webm", MUTED_GRAY)],
        [],
    ]

    open_stream = list(results_stream) + [
        [("amon-hen ❯ ", PROMPT_VIOLET), ("/open 1", WHITE_TEXT)],
        [("  ✓ Launching media player at 00:00:48.0 (cctv-people-demo.webm)", GREEN_ACCENT)],
        [],
    ]

    exit_stream = list(open_stream) + [
        [("amon-hen ❯ ", PROMPT_VIOLET), ("/exit", WHITE_TEXT)],
        [("  Farewell.", MUTED_GRAY)],
    ]

    # Build sequence
    # 1. Shell prompt
    frames.append(render_terminal([[("PS C:\\Users\\Felix\\videos> ", GREEN_ACCENT)]]))
    durations.append(400)

    # 2. Type amon-hen
    cmd = "amon-hen"
    for i in range(1, len(cmd) + 1, 2):
        frames.append(render_terminal([[(f"PS C:\\Users\\Felix\\videos> {cmd[:i]}", WHITE_TEXT)]]))
        durations.append(40)
    frames.append(render_terminal([[(f"PS C:\\Users\\Felix\\videos> {cmd}", WHITE_TEXT)]]))
    durations.append(250)

    # 3. Header appears
    frames.append(render_terminal(claude_header + [[("amon-hen ❯ ", PROMPT_VIOLET)]]))
    durations.append(800)

    # 4. Type query
    q = "a person holding an umbrella"
    for i in range(1, len(q) + 1, 2):
        temp = list(claude_header) + [[("amon-hen ❯ ", PROMPT_VIOLET), (q[:i], WHITE_TEXT)]]
        frames.append(render_terminal(temp))
        durations.append(40)

    # 5. Search executing
    temp = list(claude_header) + [
        [("amon-hen ❯ ", PROMPT_VIOLET), (q, WHITE_TEXT)],
        [("  Searching moments in vector index... (18ms)", MUTED_GRAY)],
    ]
    frames.append(render_terminal(temp))
    durations.append(500)

    # 6. Stream results
    frames.append(render_terminal(results_stream + [[("amon-hen ❯ ", PROMPT_VIOLET)]]))
    durations.append(1800)

    # 7. Type /open 1
    op = "/open 1"
    for i in range(1, len(op) + 1, 2):
        temp = list(results_stream) + [[("amon-hen ❯ ", PROMPT_VIOLET), (op[:i], WHITE_TEXT)]]
        frames.append(render_terminal(temp))
        durations.append(50)

    # 8. Open result
    frames.append(render_terminal(open_stream + [[("amon-hen ❯ ", PROMPT_VIOLET)]]))
    durations.append(1600)

    # 9. Type /exit
    ex = "/exit"
    for i in range(1, len(ex) + 1, 2):
        temp = list(open_stream) + [[("amon-hen ❯ ", PROMPT_VIOLET), (ex[:i], WHITE_TEXT)]]
        frames.append(render_terminal(temp))
        durations.append(50)

    # 10. Exit back to shell
    frames.append(render_terminal(exit_stream + [[("PS C:\\Users\\Felix\\videos> ", GREEN_ACCENT)]]))
    durations.append(3000)

    for path_name in ["demo/demo-tui-v6.gif", "demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Successfully generated Claude Code styled CLI demo ({len(frames)} frames, {Path('demo/demo-tui-v6.gif').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
