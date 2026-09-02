# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.19] - 2026-09-02

### Fixed
* **TUI Score Bar Unicode Rendering:** Fixed fallback bug in `format_score_bar` on Windows terminals to consistently render crisp Unicode block characters (`[███░░░░░░░]`) instead of ASCII dashes (`[===-------]`).

## [0.1.18] - 2026-09-02


### Fixed
* **Whisper Audio Hallucination Suppression:** Implemented average log-probability confidence thresholding (`avg_lp >= -1.0`) and n-gram repetition filtering in `WhisperTranscriber`, preventing false dialogue hallucinations on instrumental music, battle sound effects, and silent scenes.

## [0.1.17] - 2026-09-02


### Enhanced
* **Battle of Amon Hen Demo Integration:** Added full 5-minute video and audio sample clip (`battle-of-amon-hen.webm`) for testing visual actions and Whisper speech retrieval.
* **Windows Unicode Console Fix:** Auto-reconfigured standard output and error streams to UTF-8 on Windows terminals.
* **Whisper Repetition Guard:** Added hallucination loop detector during silent/instrumental audio sections.

## [0.1.15] - 2026-09-02


### Added
* **Hybrid Audio & Speech Retrieval (Whisper-Tiny ONNX + SQLite FTS5):**
  * In-memory 16kHz mono audio extraction from videos via FFmpeg (`src/amonhen/audio.py`).
  * Autoregressive speech recognition and timestamped segment transcription with Whisper-Tiny ONNX (`src/amonhen/whisper.py`).
  * High-speed full-text indexing and BM25 ranking with SQLite FTS5 (`src/amonhen/store.py`).
  * Hybrid search engine merging visual semantic vector hits with spoken dialogue cues (`src/amonhen/pipeline.py`).
  * Speech dialogue rendering (`💬 "..."`) across CLI and interactive TUI results.

## [0.1.14] - 2026-08-31


### Enhanced
* **Full Responsive Terminal Auto-Resize:** Banner header, divider lines, and footer shortcuts now adapt smoothly to any terminal width (from narrow 50-col to ultra-wide displays) with zero gap or wrapping overflow.

## [0.1.13] - 2026-08-31


### Enhanced
* **Horizontal Divider Textbox Layout:** Removed vertical borders from the input textbox and framed it with clean top and bottom horizontal divider lines.

## [0.1.12] - 2026-08-31


### Enhanced
* **Ultra-Compact 3-Row Silhouette:** Streamlined the Eagle Throne silhouette to an ultra-compact 3-row halfblock layout (`▄`, `█`, `▀`, `▒`) that fits the 3 metadata lines with zero vertical padding.

## [0.1.11] - 2026-08-31


### Enhanced
* **Reverted Textbox Header:** Clean border frame for the prompt input without title label.

## [0.1.10] - 2026-08-31


### Enhanced
* **Compact Halfblock & Dither Silhouette:** Replaced oversized ASCII art with a compact 5-row halfblock and dithered silhouette (`▄`, `█`, `▀`, `▒`) of the Seat of Seeing Eagle Throne.

## [0.1.9] - 2026-08-31


### Enhanced
* **Themed Input Frame Box:** Styled the bottom input prompt frame with titled borders (`Search or /command`) matching the header banner theme.

## [0.1.8] - 2026-08-31


### Enhanced
* **Authentic Seat of Seeing (Amon Hen) Eagle Throne ASCII Art:** Replaced simplistic block crown with detailed 9-line ASCII artwork depicting the soaring eagle wings, 4-direction eagle heads, and Seeing Eye carved pillars from the Lord of the Rings lore.

## [0.1.7] - 2026-08-31


### Enhanced
* **Natural Claude Code / Open Code TUI Flow:** Clean inline prompt without gray toolbar background or awkward bottom screen gap.
* **Unified Shortcut Legend:** Keybinding hints positioned right below the header divider for an authentic terminal UX.

## [0.1.6] - 2026-08-31


### Enhanced
* **Dedicated Full-Window TUI Initialization:** Automatic screen initialization (`\033[2J\033[H`) on launch to deliver an authentic, distraction-free full-terminal TUI experience.
* **Streamlined Toolbar & Result Layout:** Persistent prompt toolbar and rich card presentation matching the demo recording.

## [0.1.5] - 2026-08-31


### Fixed & Enhanced
* **Full-Height 11-Line Throne Pixel Art:** Implemented the exact 11-row pixel throne from the demo graphic alongside runtime metadata.
* **Toolbar Entity Parsing Fix:** Fixed XML parsing in `prompt_toolkit.HTML` by replacing HTML `&nbsp;` with standard whitespace.
* **Complete Demo Parity:** 100% pixel-and-character-level match with the demo interface including live search metrics and fixed bottom toolbar.

## [0.1.4] - 2026-08-31


### Enhanced
* **Exact Demo TUI Parity:** Refined 5-row Seat of Seeing Throne art and clean 3-line metadata header matching `demo.gif` exactly.
* **Persistent Bottom Toolbar:** Fixed bottom status line (`[Enter] Submit · /index <dir> · /open <id> · /cut <id> · /exit`) styled via `prompt_toolkit`.
* **Integrated `/index <dir>` Command:** Direct indexing from the REPL prompt with turning verb progress output and instant status update.
* **Enhanced Result Cards:** Two-line result cards with peak timestamp, focused rank #1 action hint, and visual score bars.

## [0.1.3] - 2026-08-31


### Enhanced
* **Seat of Seeing ASCII Throne Banner:** Integrated the iconic 3-tower ASCII art header and real-time metadata header into the interactive session matching the demo interface.
* **Interactive Prompt Aesthetic:** Streamlined input prompt (`> `), live search execution timer with turning verbs, and score bar alignment.
* **Windows UTF-8 Console Support:** Automatic stdout reconfiguration for crisp block rendering across Command Prompt and PowerShell.

## [0.1.2] - 2026-08-30


### Added
* **Instant Video Segment Exporter (`amon-hen cut`):** Lossless stream-copy extraction and frame-accurate re-encoded export for arbitrary start/end timestamps.
* **Interactive `/cut` Slash Command:** Instant clip exporting directly from the REPL session (`/cut <n> [output.mp4]`) with automatic +/- 2.0s padding for single-frame detections.
* **Core Cutter Module (`amonhen.cutter`):** Timestamp parsing supporting seconds, MM:SS, and HH:MM:SS formats with safe output path generation.

## [0.1.1] - 2026-08-28


### Fixed
* **macOS SQLite Extension Loading:** Added standalone Python provisioning and runtime check for macOS Python builds lacking dynamic extension support.
* **PyPI Documentation:** Tailored clean, concise `README_PYPI.md` focused on installation and quickstart usage.
* **Cross-Platform Test Compatibility:** Fixed ANSI escape code assertions across Unix and Windows CI runners.

## [0.1.0] - 2026-08-28


### Added
* **CPU-Native Moment Retrieval:** Natural language video search running entirely on CPU using Apple's MobileCLIP2 architecture and ONNX Runtime.
* **Hybrid Quantization Model:** Default distribution using `vision_model.onnx` (FP32) and `text_model_quantized.onnx` (INT8) for a ~105 MB footprint with 18.5x realtime indexing throughput.
* **Vector Storage:** SQLite vector database powered by `sqlite-vec` for embedded, single-file storage with zero server dependencies.
* **Adaptive Frame Sampling:** Motion-aware frame decoding via `imageio-ffmpeg` with embedding-based deduplication (up to 7.8x speedup over fixed per-second sampling).
* **Temporal Segment Merging:** Consecutive frame grouping into coherent start-end timestamps with per-video baseline calibration.
* **Interactive Tolkien REPL:** Terminal UI with prompt history, banner styling, visual score bars, and slash commands (`/open`, `/help`, `/exit`).
* **External Media Player Launcher:** Instant playback at matched timestamps with automatic detection for `mpv`, `vlc`, and `ffplay`.
* **Benchmark Suite:** Charades-STA evaluation harness with mIoU, R@1, and R@5 metrics and synthetic dataset generation.
* **Model Distribution:** Automated ONNX export, INT8 dynamic quantizer, numerical parity verifier, and Hugging Face publisher for `flxhrdyn/mobileclip2-s0-onnx`.
