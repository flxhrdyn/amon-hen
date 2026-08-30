# Amon Hen Project Roadmap

This document outlines the development status, architectural roadmap, and future milestones for **Amon Hen**. Community contributions and proposals are welcome for all open roadmap items.

---

## Current Status: v0.1.0 (Released)

* [x] **Core Retrieval Engine:** Natural language semantic video search on CPU using Apple's MobileCLIP2 architecture and ONNX Runtime.
* [x] **Embedded Vector Database:** Single-file vector storage via `sqlite-vec` in SQLite with zero background daemons.
* [x] **Adaptive Frame Sampler:** 3-gate motion filtering (aHash perceptual diff, Laplacian sharpness, and embedding deduplication) delivering 4.8x to 18.5x realtime throughput.
* [x] **Temporal Segment Merging:** Consecutive frame clustering into start-end intervals with per-video noise score calibration.
* [x] **Interactive Tolkien TUI/REPL:** Terminal interface with command history, score bars, and external player launching (`mpv`, `vlc`, `ffplay`).
* [x] **Evaluation Benchmark Suite:** Charades-STA benchmark harness measuring mIoU, Recall@1, and Recall@5.
* [x] **Official Model Distribution:** Pre-converted Hybrid FP32-vision + INT8-text ONNX artifacts hosted on Hugging Face at [`felixhrdyn/mobileclip2-s0-onnx`](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx).

---

## Planned Milestones & Future Work

We welcome community pull requests and design proposals for the following milestones:

### 1. Instant Video Segment Exporter (`amon-hen cut`)
* **Goal:** Extract matching video moments directly into standalone video clips without re-encoding.
* **Scope:**
  * [x] Add CLI command: `amon-hen cut <video_path> --start <timestamp> --end <timestamp> -o output.mp4`.
  * [x] Add slash command in interactive mode: `/cut <result_number> [output_path]`.
  * [x] Use FFmpeg stream copying (`-c copy -ss <start> -to <end>`) for sub-second lossless extraction.
  * [x] Optional frame-accurate re-encoding mode (`--reencode`).
* **Status:** Completed (Released in `v0.1.2`).


---

### 2. Multi-Model Support (`mobileclip2-s2` & Custom Models)
* **Goal:** Allow users to choose larger vision-language models for higher resolution retrieval.
* **Scope:**
  * Export and package Apple's `MobileCLIP2-S2` (~36M parameters) to ONNX and distribute on Hugging Face (`felixhrdyn/mobileclip2-s2-onnx`).
  * Add CLI flag `--model mobileclip2-s2` to `index` and `search`.
  * Support custom user-provided ONNX vision/text model pairs via configuration file.
* **Status:** Open for Contribution.

---

### 3. Speech & Audio Search Integration (Whisper ONNX)
* **Goal:** Enable hybrid search across both visual video content and spoken speech.
* **Scope:**
  * Extract audio track using `imageio-ffmpeg`.
  * Transcribe speech on CPU using lightweight Whisper ONNX (e.g. Whisper-Tiny or Whisper-Base INT8).
  * Store timestamped text segments in SQLite FTS5 (Full-Text Search).
  * Hybrid query routing: detect whether search query is visual or spoken dialogue.
* **Status:** Planned.

---

### 4. Local Web UI & Timeline Scrubber (`amon-hen serve`)
* **Goal:** Browser-based dashboard for interactive search and visual video exploration.
* **Scope:**
  * Add command `amon-hen serve --port 8000` launching a lightweight FastAPI / local server.
  * Interactive HTML5 video player with segment heatmaps on the seekbar.
  * Instant search bar with visual thumbnails for matching frames.
* **Status:** Planned.

---

## How to Contribute to the Roadmap

If you would like to work on any of the roadmap items above:
1. Check the [Issues tracker](https://github.com/flxhrdyn/amon-hen/issues) or open a new issue titled `[Feature Proposal]: <Milestone Name>`.
2. Discuss your implementation plan with maintainers.
3. Review our [Contributing Guide](CONTRIBUTING.md) and submit a pull request.
