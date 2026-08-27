"""Render complete End-to-End (E2E) demo GIF for Amon Hen in Royal Gondor Midnight Navy & Mithril White."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 900
HEIGHT = 580

# Royal Gondor Banner Palette: Deep Midnight Navy & Mithril Silver-White
BG_COLOR = (8, 14, 44)           # #080E2C Deep Gondor Midnight Navy
TITLE_BG = (5, 9, 30)            # #05091E Titlebar
PANEL_BG = (14, 23, 62)          # #0E173E Royal Navy Card surface
BORDER_COL = (32, 48, 105)       # #203069 Royal Border
HIGHLIGHT_BG = (22, 34, 88)      # #162258 Selected Card Surface
BAR_EMPTY = (20, 30, 72)         # #141E48 Empty score track

# Gondor Accents
WHITE_PRIMARY = (255, 255, 255)  # #FFFFFF Pure Mithril Silver-White
STARLIGHT_BLUE = (165, 195, 255) # #A5C3FF Gondor Starlight Blue
MUTED_NAVY = (120, 140, 185)     # #788CB9 Muted Silver-Navy text

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

    # Monochrome window controls
    draw.ellipse([14, 10, 24, 20], fill=(45, 60, 105))
    draw.ellipse([30, 10, 40, 20], fill=(45, 60, 105))
    draw.ellipse([46, 10, 56, 20], fill=WHITE_PRIMARY)
    draw.text((WIDTH // 2 - 50, 8), "amon-hen", fill=MUTED_NAVY, font=font_small)

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
    query_text: str = "",
    show_query_card: bool = False,
    show_results: bool = False,
    selected_rank: int | None = None,
    notification_msg: str | None = None,
    input_text: str = "",
    show_cursor: bool = True,
) -> Image.Image:
    """Render full OpenCode TUI screen in Gondor Navy & White."""
    img, draw = create_base_window()

    # 1. Top Header Box with Tolkien Tagline
    draw.rounded_rectangle([20, 44, WIDTH - 20, 114], radius=4, fill=PANEL_BG, outline=BORDER_COL)
    draw.text((36, 52), "Amon Hen v0.1.0", fill=WHITE_PRIMARY, font=font_bold)
    draw.text((180, 53), '· "From the Seat of Seeing, no moment remains hidden."', fill=STARLIGHT_BLUE, font=font_main)
    draw.text((36, 76), "Model: MobileCLIP2-S2 (CPU)   Storage: sqlite-vec   Index: 1 video (49 frames)", fill=MUTED_NAVY, font=font_small)
    draw.text((36, 93), "~/videos/cctv-people-demo.webm", fill=MUTED_NAVY, font=font_small)

    # 2. Query Card
    if show_query_card:
        draw.rounded_rectangle([20, 122, WIDTH - 20, 158], radius=4, fill=PANEL_BG, outline=BORDER_COL)
        draw.text((36, 131), f"> {query_text}", fill=WHITE_PRIMARY, font=font_main)

    # 3. Results Container Cards
    if show_results:
        bar_x = WIDTH - 260

        # Card #1 (Selected Active Card)
        is_sel_1 = (selected_rank == 1)
        c1_bg = HIGHLIGHT_BG if is_sel_1 else PANEL_BG
        c1_border = WHITE_PRIMARY if is_sel_1 else BORDER_COL
        draw.rounded_rectangle([20, 168, WIDTH - 20, 240], radius=4, fill=c1_bg, outline=c1_border, width=2 if is_sel_1 else 1)
        draw.text((36, 177), "#1   00:00:37.0 -> 00:01:06.0", fill=WHITE_PRIMARY, font=font_bold)
        draw.text((36, 198), "File: cctv-people-demo.webm   Peak: 00:00:48.0", fill=STARLIGHT_BLUE, font=font_small)
        draw.text((36, 218), "=> Action: Type /open 1 to play moment in VLC", fill=WHITE_PRIMARY, font=font_small)

        # Smooth White score bar #1
        draw.rounded_rectangle([bar_x, 188, bar_x + 120, 200], radius=2, fill=BAR_EMPTY)
        draw.rounded_rectangle([bar_x, 188, bar_x + 90, 200], radius=2, fill=WHITE_PRIMARY)
        draw.text((bar_x + 135, 184), "0.261", fill=WHITE_PRIMARY, font=font_bold)

        # Card #2
        draw.rounded_rectangle([20, 248, WIDTH - 20, 300], radius=4, fill=PANEL_BG, outline=BORDER_COL)
        draw.text((36, 257), "#2   00:00:04.0 -> 00:00:19.0", fill=STARLIGHT_BLUE, font=font_bold)
        draw.text((36, 278), "File: cctv-people-demo.webm   Peak: 00:00:11.0", fill=MUTED_NAVY, font=font_small)
        draw.rounded_rectangle([bar_x, 265, bar_x + 120, 277], radius=2, fill=BAR_EMPTY)
        draw.rounded_rectangle([bar_x, 265, bar_x + 82, 277], radius=2, fill=STARLIGHT_BLUE)
        draw.text((bar_x + 135, 261), "0.247", fill=STARLIGHT_BLUE, font=font_bold)

        # Card #3
        draw.rounded_rectangle([20, 308, WIDTH - 20, 360], radius=4, fill=PANEL_BG, outline=BORDER_COL)
        draw.text((36, 317), "#3   00:00:24.0 -> 00:00:32.0", fill=STARLIGHT_BLUE, font=font_bold)
        draw.text((36, 338), "File: cctv-people-demo.webm   Peak: 00:00:28.0", fill=MUTED_NAVY, font=font_small)
        draw.rounded_rectangle([bar_x, 325, bar_x + 120, 337], radius=2, fill=BAR_EMPTY)
        draw.rounded_rectangle([bar_x, 325, bar_x + 75, 337], radius=2, fill=STARLIGHT_BLUE)
        draw.text((bar_x + 135, 321), "0.227", fill=STARLIGHT_BLUE, font=font_bold)

    # 4. Flash Notification Toast
    if notification_msg:
        draw.rounded_rectangle([20, 372, WIDTH - 20, 408], radius=4, fill=HIGHLIGHT_BG, outline=WHITE_PRIMARY)
        draw.text((36, 380), f"=> {notification_msg}", fill=WHITE_PRIMARY, font=font_main)

    # 5. Pinned Bottom Input Box
    draw.rounded_rectangle([20, 444, WIDTH - 20, 492], radius=4, fill=PANEL_BG, outline=WHITE_PRIMARY, width=2)
    draw.text((36, 456), "amon-hen > ", fill=STARLIGHT_BLUE, font=font_bold)
    draw.text((130, 456), input_text, fill=WHITE_PRIMARY, font=font_main)

    if show_cursor:
        cx = 130 + int(draw.textlength(input_text, font=font_main))
        draw.rectangle([cx + 2, 458, cx + 10, 474], fill=WHITE_PRIMARY)

    # Footer Shortcuts
    draw.text((24, 508), "[Enter] Submit  ·  /open <id> Play Moment  ·  /videos List  ·  /exit Quit", fill=MUTED_NAVY, font=font_small)
    draw.text((WIDTH - 160, 508), "MobileCLIP2 · CPU", fill=MUTED_NAVY, font=font_small)

    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []

    # === STAGE 1: Shell CLI Indexing ===
    frames.append(render_shell_screen([
        ("PS C:\\Users\\Felix\\videos> ", STARLIGHT_BLUE)
    ]))
    durations.append(450)

    idx_cmd = "amon-hen index demo/ --sampler adaptive"
    for i in range(1, len(idx_cmd) + 1, 3):
        frames.append(render_shell_screen([
            (f"PS C:\\Users\\Felix\\videos> {idx_cmd[:i]}", WHITE_PRIMARY)
        ]))
        durations.append(35)
    frames.append(render_shell_screen([
        (f"PS C:\\Users\\Felix\\videos> {idx_cmd}", WHITE_PRIMARY)
    ]))
    durations.append(300)

    frames.append(render_shell_screen([
        (f"PS C:\\Users\\Felix\\videos> {idx_cmd}", WHITE_PRIMARY),
        ("Indexing cctv-people-demo.webm [==========..........]  50% | 18.5x RT", STARLIGHT_BLUE),
    ]))
    durations.append(300)

    frames.append(render_shell_screen([
        (f"PS C:\\Users\\Felix\\videos> {idx_cmd}", WHITE_PRIMARY),
        ("Indexing cctv-people-demo.webm [====================] 100% | 18.5x RT", WHITE_PRIMARY),
        ("=> Indexed 1 video(s), 49 keyframes stored in ~/.amonhen/index.db (2.3s)", STARLIGHT_BLUE),
        ("", MUTED_NAVY),
        ("PS C:\\Users\\Felix\\videos> ", STARLIGHT_BLUE),
    ]))
    durations.append(900)

    launch_cmd = "amon-hen"
    for i in range(1, len(launch_cmd) + 1, 2):
        frames.append(render_shell_screen([
            (f"PS C:\\Users\\Felix\\videos> {idx_cmd}", WHITE_PRIMARY),
            ("=> Indexed 1 video(s), 49 keyframes stored in ~/.amonhen/index.db (2.3s)", STARLIGHT_BLUE),
            ("", MUTED_NAVY),
            (f"PS C:\\Users\\Felix\\videos> {launch_cmd[:i]}", WHITE_PRIMARY),
        ]))
        durations.append(40)

    # === STAGE 2: Transition into Interactive OpenCode TUI Screen ===
    frames.append(render_tui_screen(input_text="", show_cursor=True))
    durations.append(850)

    q = "a person holding an umbrella"
    for i in range(1, len(q) + 1, 2):
        frames.append(render_tui_screen(input_text=q[:i], show_cursor=True))
        durations.append(35)
    frames.append(render_tui_screen(input_text=q, show_cursor=True))
    durations.append(300)

    frames.append(render_tui_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        input_text="",
        show_cursor=True,
    ))
    durations.append(1800)

    op = "/open 1"
    for i in range(1, len(op) + 1, 2):
        frames.append(render_tui_screen(
            query_text=q,
            show_query_card=True,
            show_results=True,
            selected_rank=1,
            input_text=op[:i],
            show_cursor=True,
        ))
        durations.append(40)
    frames.append(render_tui_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        selected_rank=1,
        input_text=op,
        show_cursor=True,
    ))
    durations.append(250)

    frames.append(render_tui_screen(
        query_text=q,
        show_query_card=True,
        show_results=True,
        selected_rank=1,
        notification_msg="Launching media player at 00:00:48.0 (cctv-people-demo.webm)...",
        input_text="",
        show_cursor=True,
    ))
    durations.append(2400)

    ex = "/exit"
    for i in range(1, len(ex) + 1, 2):
        frames.append(render_tui_screen(
            query_text=q,
            show_query_card=True,
            show_results=True,
            selected_rank=1,
            notification_msg="Launching media player at 00:00:48.0 (cctv-people-demo.webm)...",
            input_text=ex[:i],
            show_cursor=True,
        ))
        durations.append(40)

    # === STAGE 3: Clean Exit back to Shell ===
    frames.append(render_shell_screen([
        ("PS C:\\Users\\Felix\\videos> amon-hen", WHITE_PRIMARY),
        ("Farewell. The seeing closes.", STARLIGHT_BLUE),
        ("", MUTED_NAVY),
        ("PS C:\\Users\\Felix\\videos> ", STARLIGHT_BLUE),
    ]))
    durations.append(3000)

    for path_name in ["demo/demo-tui-gondor.gif", "demo/demo-tui.gif", "demo/demo.gif"]:
        out_path = Path(path_name)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
    print(f"Successfully generated Royal Gondor Navy & White demo ({len(frames)} frames, {Path('demo/demo-tui-gondor.gif').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
