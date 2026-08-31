# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
