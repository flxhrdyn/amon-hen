"""Render authentic OpenCode TUI styled demo GIF for Amon Hen."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 580

# OpenCode Dark Slate Theme
BG_COLOR = (22, 24, 30)          # Slate obsidian
TITLE_BG = (16, 17, 22)          # Titlebar
PANEL_BG = (28, 31, 40)          # Card surface
BORDER_COL = (55, 60, 78)        # Border line
HIGHLIGHT_BORDER = (245, 185, 65)# Active gold border
INPUT_BORDER = (170, 130, 245)   # Purple input box border

TEXT_WHITE = (245, 245, 250)     # Primary text
TEXT_SUB = (160, 165, 180)       # Subtitle text
TEXT_MUTED = (120, 125, 145)     # Gray metadata
TEXT_CYAN = (130, 195, 245)      # Starlight cyan timestamp
TEXT_GREEN = (80, 230, 140)      # Success green
TEXT_GOLD = (245, 185, 65)       # Gold title

FONT_PATH = "C:/Windows/Fonts/consola.ttf" if os.path.exists("C:/Windows/Fonts/consola.ttf") else None
FONT_BOLD_PATH = "C:/Windows/Fonts/consolab.ttf" if os.path.exists("C:/Windows/Fonts/consolab.ttf") else FONT_PATH

if FONT_PATH:
    font_main = ImageFont.truetype(FONT_PATH, 15)
    font_bold = ImageFont.truetype(FONT_BOLD_PATH, 15)
    font_small = ImageFont.truetype(FONT_PATH, 13)
else:
    font_main = font_bold = font_small = ImageFont.load_default()


def create_base_window() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Window titlebar
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BG)
    draw.line([0, 32, WIDTH, 32], fill=BORDER_COL)

    # macOS window controls
    draw.ellipse([14, 10, 24, 20], fill=(239, 68, 68))
    draw.ellipse([30, 10, 40, 20], fill=(245, 158, 11))
    draw.ellipse([46, 10, 56, 20], fill=(34, 197, 94))
    draw.text((WIDTH // 2 - 50, 8), "amon-hen", fill=TEXT_MUTED, font=font_small)

    # 1. Top Header Box (OpenCode style)
    draw.rounded_rectangle([20, 44, WIDTH - 20, 104], radius=4, fill=PANEL_BG, outline=BORDER_COL)
    draw.text((36, 52), "Amon Hen v0.1.0", fill=TEXT_GOLD, font=font_bold)
    draw.text((180, 53), "· The Seat of Seeing", fill=TEXT_SUB, font=font_main)
    draw.text((36, 76), "Model: MobileCLIP2-S2 (CPU)   Storage: sqlite-vec   Index: 1 video (49 frames)", fill=TEXT_CYAN, font=font_small)

    return img, draw


def render_opencode_screen(
    query_text: str = "",
    show_query_card: bool = False,
    show_results: bool = False,
    selected_rank: int | None = None,
    notification_msg: str | None = None,
    input_text: str = "",
    show_cursor: bool = True,
) -> Image.Image:
    img, draw = create_base_window()

    # 2. Query Card
    if show_query_card:
        draw.rounded_rectangle([20, 114, WIDTH - 20, 152], radius=4, fill=PANEL_BG, outline=BORDER_COL)
        draw.text((36, 124), f"> {query_text}", fill=TEXT_WHITE, font=font_main)

    # 3. Results Container Cards
    if show_results:
        bar_x = WIDTH - 260

        # Card #1
        is_sel_1 = (selected_rank == 1)
        c1_bg = (34, 38, 52) if is_sel_1 else PANEL_BG
        c1_border = HIGHLIGHT_BORDER if is_sel_1 else BORDER_COL
        draw.rounded_rectangle([20, 164, WIDTH - 20, 238], radius=4, fill=c1_bg, outline=c1_border, width=2 if is_sel_1 else 1)
        draw.text((36, 174), "#1   00:00:37.0 -> 00:01:06.0", fill=TEXT_CYAN, font=font_bold)
        draw.text((36, 196), "File: cctv-people-demo.webm   Peak: 00:00:48.0", fill=TEXT_SUB, font=font_small)
        draw.text((36, 216), "=> Action: Type /open 1 to play moment in VLC", fill=TEXT_GREEN, font=font_small)

        # Smooth score bar #1
        draw.rounded_rectangle([bar_x, 186, bar_x + 120, 198], radius=2, fill=(45, 50, 68))
        draw.rounded_rectangle([bar_x, 186, bar_x + 90, 198], radius=2, fill=TEXT_GOLD)
        draw.text((bar_x + 135, 182), "0.261", fill=TEXT_GREEN, font=font_bold)

        # Card #2
        draw.rounded_rectangle([20, 248, WIDTH - 20, 302], radius=4, fill=PANEL_BG, outline=BORDER_COL)
        draw.text((36, 258), "#2   00:00:04.0 -> 00:00:19.0", fill=TEXT_CYAN, font=font_bold)
        draw.text((36, 280), "File: cctv-people-demo.webm   Peak: 00:00:11.0", fill=TEXT_SUB, font=font_small)
        draw.rounded_rectangle([bar_x, 266, bar_x + 120, 278], radius=2, fill=(45, 50, 68))
        draw.rounded_rectangle([bar_x, 266, bar_x + 82, 278], radius=2, fill=TEXT_GOLD)
        draw.text((bar_x + 135, 262), "0.247", fill=TEXT_GREEN, font=font_bold)

        # Card #3
        draw.rounded_rectangle([20, 312, WIDTH - 20, 366], radius=4, fill=PANEL_BG, outline=BORDER_COL)
        draw.text((36, 322), "#3   00:00:24.0 -> 00:00:32.0", fill=TEXT_CYAN, font=font_bold)
        draw.text((36, 344), "File: cctv-people-demo.webm   Peak: 00:00:28.0", fill=TEXT_SUB, font=font_small)
        draw.rounded_rectangle([bar_x, 330, bar_x + 120, 342], radius=2, fill=(45, 50, 68))
        draw.rounded_rectangle([bar_x, 330, bar_x + 75, 342], radius=2, fill=TEXT_GOLD)
        draw.text((bar_x + 135, 326), "0.227", fill=TEXT_GREEN, font=font_bold)

    # 4. Flash Notification Toast
    if notification_msg:
        draw.rounded_rectangle([20, 378, WIDTH - 20, 414], radius=4, fill=(25, 48, 38), outline=TEXT_GREEN)
        draw.text((36, 386), f"=> {notification_msg}", fill=TEXT_GREEN, font=font_main)

    # 5. Pinned Bottom Input Box (OpenCode Style)
    draw.rounded_rectangle([20, 444, WIDTH - 20, 492], radius=4, fill=PANEL_BG, outline=INPUT_BORDER, width=2)
    draw.text((36, 456), "amon-hen > ", fill=INPUT_BORDER, font=font_bold)
    draw.text((130, 456), input_text, fill=TEXT_WHITE, font=font_main)

    if show_cursor:
        cx = 130 + int(draw.textlength(input_text, font=font_main))
        draw.rectangle([cx + 2, 458, cx + 10, 474], fill=TEXT_WHITE)

    # Footer Shortcuts
    draw.text((24, 508), "[Enter] Submit  ·  /open <id> Play Moment  ·  /videos List  ·  /exit Quit", fill=TEXT_MUTED, font=font_small)
    draw.text((WIDTH - 160, 508), "MobileCLIP2 · CPU", fill=TEXT_MUTED, font=font_small)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    # Scene 1: Initial Screen (Ready)
    frames.append(render_opencode_screen(input_text="", show_cursor=True))
    durations.append(900)

    # Scene 2: Type Query in Input Box
    q = "a person holding an umbrella"
    for i in range(1, len(q) + 1, 2):
        frames.append(render_opencode_screen(input_text=q[:i], show_cursor=True))
        durations.append(40)
    frames.append(render_opencode_screen(input_text=q, show_cursor=True))
    durations.append(300)

    # Scene 3: Press Enter -> Query Card & Results Appear
    frames.append(render_opencode_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        input_text="",
        show_cursor=True,
    ))
    durations.append(1800)

    # Scene 4: Type /open 1 in Input Box
    op = "/open 1"
    for i in range(1, len(op) + 1, 2):
        frames.append(render_opencode_screen(
            query_text=q,
            show_query_card=True,
            show_results=True,
            selected_rank=1,
            input_text=op[:i],
            show_cursor=True,
        ))
        durations.append(45)
    frames.append(render_opencode_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        selected_rank=1,
        input_text=op,
        show_cursor=True,
    ))
    durations.append(300)

    # Scene 5: Submit -> Player Launch Notification Card Appears
    frames.append(render_opencode_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        selected_rank=1,
        notification_msg="Launching media player at 00:00:48.0 (cctv-people-demo.webm)...",
        input_text="",
        show_cursor=True,
    ))
    durations.append(2600)

    # Scene 6: Type /exit
    ex = "/exit"
    for i in range(1, len(ex) + 1, 2):
        frames.append(render_opencode_screen(
            query_text=q,
            show_query_card=True,
            show_results=True,
            selected_rank=1,
            notification_msg="Launching media player at 00:00:48.0 (cctv-people-demo.webm)...",
            input_text=ex[:i],
            show_cursor=True,
        ))
        durations.append(45)

    frames.append(render_opencode_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        selected_rank=1,
        notification_msg="Farewell.",
        input_text="",
        show_cursor=True,
    ))
    durations.append(2500)

    for path_name in ["demo/demo-tui-v10.gif", "demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Successfully generated OpenCode styled TUI demo ({len(frames)} frames, {Path('demo/demo-tui-v10.gif').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
