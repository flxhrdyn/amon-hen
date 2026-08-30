# Stage 6 Spec: Instant Video Segment Exporter (`amon-hen cut` & `/cut`)

## 1. Goal & Motivation
Amon Hen allows users to search video archives using natural language queries and returns matching temporal segments (`start - end`). To complete the workflow, users need an instant, frictionless way to extract those matching moments into standalone video clips without leaving the CLI or REPL session, and without heavy re-encoding delays.

## 2. Technical Architecture

### 2.1 Core Module (`src/amonhen/cutter.py`)
This module handles all timestamp parsing, output path generation, and FFmpeg execution for video cutting.

#### Key Functions:
* `parse_timestamp(val: str | float | int) -> int`
  * Converts float/integer seconds (`"75.5"`, `75`, `75.5`) -> milliseconds (`75500`).
  * Converts `MM:SS` or `MM:SS.s` (`"01:15"`, `"01:15.5"`) -> milliseconds (`75500`).
  * Converts `HH:MM:SS` or `HH:MM:SS.s` (`"00:01:15"`, `"01:02:03.4"`) -> milliseconds.
  * Raises `ValueError` for malformed time strings.

* `format_timestamp_tag(ms: int) -> str`
  * Converts milliseconds to filename-friendly string (e.g. `75500` -> `01m15s` or `01h02m03s`).

* `generate_clip_path(video_path: Path | str, start_ms: int, end_ms: int, out_path: Path | str | None = None) -> Path`
  * If `out_path` is specified: returns `Path(out_path)`.
  * If `out_path` is `None`: returns `<video_stem>_clip_<start_tag>_<end_tag>.mp4` in the current working directory.

* `cut_video_segment(video_path: Path | str, start_ms: int, end_ms: int, out_path: Path | str | None = None, reencode: bool = False) -> Path`
  * Validates that `video_path` exists and `start_ms <= end_ms`.
  * Generates destination `Path`.
  * Executes FFmpeg via `imageio_ffmpeg.get_ffmpeg_exe()`.
  * **Stream copy mode (`reencode=False`):**
    `ffmpeg -ss <start_s> -to <end_s> -i <video_path> -c copy -avoid_negative_ts make_zero -y <out_path>`
  * **Re-encode mode (`reencode=True`):**
    `ffmpeg -ss <start_s> -to <end_s> -i <video_path> -c:v libx264 -c:a aac -crf 20 -preset fast -y <out_path>`
  * Raises `FFmpegError` if FFmpeg returns a non-zero exit code.

### 2.2 CLI Command (`src/amonhen/cli.py`)
Add `cut` command to the Typer app:
```bash
amon-hen cut <video_path> --start <time> --end <time> [-o output.mp4] [--reencode] [--json]
```

Options:
* `video_path`: Path to source video file (Argument).
* `--start, -s`: Start timestamp string (Option, required).
* `--end, -e`: End timestamp string (Option, required).
* `--output, -o`: Custom output filename (Option, default: None -> auto-generated).
* `--reencode`: Force video/audio re-encoding for frame-accurate boundary cutting (Option, flag).
* `--json`: Emit JSON response to stdout: `{"status": "ok", "video_path": "...", "clip_path": "...", "start_ms": 1000, "end_ms": 5000, "reencoded": false}`.

### 2.3 Interactive REPL Slash Command (`src/amonhen/interactive.py`)
Extend `handle_slash_command`:
* Command syntax: `/cut <number> [output_filename]` (e.g. `/cut 1` or `/cut 1 highlight.mp4`).
* Resolves segment from `last_results[number - 1]`.
* If `seg.start_ms == seg.end_ms` (single frame detection), applies +/- 2000 ms padding (`max(0, seg.start_ms - 2000)` to `seg.end_ms + 2000`).
* Calls `cut_video_segment`.
* Prints success message with the output file path.

## 3. Test Coverage Strategy (`tests/test_cutter.py`)
* Unit tests for `parse_timestamp` (seconds, floats, MM:SS, HH:MM:SS, invalid input).
* Unit tests for `generate_clip_path` and `format_timestamp_tag`.
* Functional tests for `cut_video_segment` with synthetic/real sample video in `tmp_path`.
* CLI tests for `amon-hen cut` with text and `--json` outputs.
* Interactive REPL tests for `/cut` command execution with padding and custom naming.
