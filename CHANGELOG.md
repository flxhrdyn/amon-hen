# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
