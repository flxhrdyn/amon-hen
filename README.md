# Amon Hen

> *"From the Seat of Seeing, no moment remains hidden."*

[![CI](https://github.com/flxhrdyn/amon-hen/actions/workflows/ci.yml/badge.svg)](https://github.com/flxhrdyn/amon-hen/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/amon-hen?color=blue)](https://pypi.org/project/amon-hen/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Hugging Face Models](https://img.shields.io/badge/Hugging%20Face-Models-orange.svg)](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx)

A fast, lightweight command-line tool and Python library for natural language moment retrieval across local video files. Runs entirely on CPU without discrete GPUs, background daemons, or cloud dependencies.

![Amon Hen Demo](https://raw.githubusercontent.com/flxhrdyn/amon-hen/main/demo/demo.gif)

---

## Overview

Finding specific moments across long video archives typically requires either high-end GPUs to run large multimodal models or naive per-second extraction that produces thousands of redundant frames and bloated vector stores.

Amon Hen bridges this gap by combining:
- **MobileCLIP2 ([`felixhrdyn/mobileclip2-s0-onnx`](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx)):** CPU-optimized visual-semantic embeddings (512 dimensions) running on a hybrid FP32-vision + INT8-quantized text pipeline (approx. 105 MB total RAM footprint).
- **Three-Gate Adaptive Sampler:** Filters near-duplicate frames via perceptual hashing, drops blurry frames via Laplacian variance, and eliminates semantic duplicates before storage.
- **Temporal Segment Merging:** Aggregates contiguous high-similarity frames into coherent time intervals (`start - end`) with peak representative timestamps.
- **Statistical Score Calibration:** Computes empirical text-to-image noise baselines per video to eliminate false positive results on unmatched queries.
- **Embedded Vector Database:** Stores vectors in local SQLite databases via `sqlite-vec`.

---

## Installation

Install using `uv` (recommended) or `pipx`:

```bash
uv tool install amon-hen
# or
pipx install amon-hen
```

On first invocation of `index` or `search`, the official CPU-optimized model artifacts (approx. 105 MB total) are downloaded automatically from [`felixhrdyn/mobileclip2-s0-onnx`](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx) to `~/.amonhen/models/`. You can pre-fetch them manually:


```bash
amon-hen setup
```

### Dependencies
- Python 3.11+
- FFmpeg (bundled automatically via `imageio-ffmpeg` if not present in `PATH`)

---

## Quick Start

### 1. Interactive Mode (TUI)
Launch the interactive REPL with query history (`↑`/`↓`) and slash commands:

```bash
amon-hen
```

Within the interactive session:
- `<query>`: Search moments across indexed videos.
- `/open <n>`: Jump to and play result `#n` in your default media player.
- `/videos`: List all indexed videos.
- `/stats`: Display index breakdown and frame statistics.
- `/exit`: Quit the session.

### 2. Index Videos
Index a single file or an entire directory:

```bash
amon-hen index /path/to/videos/ --sampler adaptive
```

Options:
- `--fps FLOAT`: Target extraction rate before gating (default: `1.0`).
- `--sampler [fixed|adaptive]`: Frame selection strategy (default: `fixed`).
- `--embed-dedup FLOAT`: Cosine similarity threshold to skip semantically identical frames (e.g. `0.98`).
- `--db PATH`: Custom index database location (default: `~/.amonhen/index.db`).

### 3. One-Shot Search
Search directly from shell scripts or pipelines:

```bash
amon-hen search "a person holding an umbrella"
```

Output:
```
 1. 00:00:37.0 - 00:01:06.0  0.261  cctv-people-demo.webm
 2. 00:00:04.0 - 00:00:19.0  0.247  cctv-people-demo.webm
 3. 00:00:24.0 - 00:00:32.0  0.227  cctv-people-demo.webm
```

Options:
- `-k, --limit INTEGER`: Maximum number of segments returned (default: `10`).
- `--merge-gap FLOAT`: Maximum gap in seconds between candidate frames to merge into one segment (default: `4.0`).
- `--min-score FLOAT`: Explicit cosine similarity threshold override.
- `--no-calibrate`: Disable automatic statistical baseline filtering.
- `--json`: Output raw structured JSON to `stdout` (human logs go to `stderr`).

### 4. Inspect Index and Statistics

```bash
# List indexed videos and frame counts
amon-hen videos

# Inspect indexing breakdown across sampler gates
amon-hen stats
```

---

## Command-Line Interface

All commands support `--json` for scripting and pipeline composition:

| Command | Description |
|---|---|
| `amon-hen` | Launch the interactive REPL session with history navigation and media player integration. |
| `amon-hen index <paths>...` | Extract, filter, embed, and index video frames into SQLite. |
| `amon-hen search "<query>"` | Retrieve matching video segments by natural language query. |
| `amon-hen videos` | List all indexed videos, durations, and stored frame counts. |
| `amon-hen stats` | Display total video counts, frame totals, and gate filtering breakdown. |
| `amon-hen setup` | Download and verify model artifacts ahead of time. |
| `amon-hen version` | Print current package version. |

---

## Architecture

Amon Hen uses a strictly decoupled, one-directional pipeline:

```
Video File
    │
    ▼
[ amonhen.decode ]       FFmpeg subprocess streaming rawvideo with internal fps decimation
    │
    ▼
[ amonhen.sample ]       Gate 1: Low-resolution average hash perceptual deduplication
    │                    Gate 2: Spatial Laplacian sharpness / blur filtering
    │
    ▼
[ amonhen.encode ]       MobileCLIP2 ONNX batch vision encoder (L2 normalized vectors)
    │
    ▼
[ amonhen.pipeline ]     Gate 3: Embedding cosine deduplication against prior frame
    │                    Statistical noise baseline calibration
    ▼
[ amonhen.store ]        SQLite vector persistence via sqlite-vec (vec0 virtual table)
    │
    ▼
[ amonhen.segment ]      Temporal clustering and score-weighted segment aggregation
```

---

## Benchmarks

### Video Moment Retrieval: Charades-STA (Zero-Shot Baseline)

Amon Hen is designed as a lightweight, zero-GPU semantic frame search engine with post-hoc temporal clustering. Evaluated zero-shot (without video-specific training or fine-tuning) on 20 Charades-STA test videos (56 temporal grounding queries):

| Sampler Configuration | R@1 (IoU=0.3) | R@1 (IoU=0.5) | R@5 (IoU=0.3) | mIoU | Indexing Speed | Latency | Storage / Hour |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fixed (1.0 fps)** | **0.393** | **0.250** | **0.696** | **0.250** | 1.7x Realtime | 359 ms | 13.0 MB |
| **Adaptive (Default)** | 0.250 | 0.107 | 0.607 | 0.155 | **4.8x Realtime** | **335 ms** | 12.9 MB |
| **Adaptive + Embed-Dedup** | 0.250 | 0.107 | 0.607 | 0.166 | 4.7x Realtime | 385 ms | 12.9 MB |

### Evaluation & Design Insights:
- **Search Usability (Recall@5):** For practical desktop search, **Recall@5 = 0.696** indicates that the relevant video moment is surfaced in the top-5 candidates approx. 70% of the time in pure zero-shot mode on CPU.
- **Zero-Shot vs Supervised Context:** Unlike heavy supervised temporal grounding architectures (e.g. VSLNet, 2D-TAN, Moment-DETR) that require GPU clusters and dataset-specific training, Amon Hen operates zero-shot with an approx. 12M parameter vision backbone, consuming < 200 MB RAM and 0% GPU.
- **Sampler Trade-offs:**
  - **Fixed 1.0 fps:** Highest retrieval fidelity (R@1@0.3 = 0.393, R@5 = 0.696), recommended when search precision is the top priority.
  - **Adaptive Sampler:** Yields 2.8x faster indexing throughput (up to 4.8x Realtime) via perceptual aHash and Laplacian sharpness gating, ideal for long-form video archives.

*Metrics:*
- **R@K (IoU=θ):** Fraction of queries where at least one top-K segment achieves temporal IoU >= θ with ground truth.
- **mIoU:** Mean Intersection-over-Union across top-1 predictions.
- **Indexing Speed:** Processing throughput expressed as a multiple of video playback duration.

To reproduce:

```bash
# 1. Download and extract Charades-STA test subset (20 videos, approx. 25 MB via ZIP range requests)
uv run python tools/prepare_charades_sta.py --videos 20 --out benchmarks/charades_sta_subset

# 2. Run benchmark sweep
uv run python -m benchmarks.run --data-dir benchmarks/charades_sta_subset
```

### FP32 vs INT8 Quantization Comparison

Measured on CPU (4 threads) using ONNX Runtime with official [`felixhrdyn/mobileclip2-s0-onnx`](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx) artifacts:

| Component | FP32 Size | INT8 Size | Compression | Latency (FP32 -> INT8) | Recommendation |
|---|:---:|:---:|:---:|:---:|---|
| **Text Encoder** | 242.3 MB | 61.3 MB | -74.7% | 21.6 ms -> **10.3 ms** (2.09x faster) | **INT8** (optimal speed & low RAM) |
| **Vision Backbone** | 43.4 MB | 11.3 MB | -74.0% | **111.8 ms** -> 1,393.1 ms | **FP32** (optimal for FastViT CPU kernels) |
| **Full Pipeline** | **285.7 MB** | **72.7 MB** | **-74.6%** | Hybrid: **18.5x Realtime** | **Hybrid** (FP32 Vision + INT8 Text: approx. 105 MB total) |


---

## Capabilities and Scope

### What Amon Hen matches
- **Objects and Entities:** e.g., "a red car", "a person wearing a helmet", "a dog on grass".
- **Visual Attributes and Settings:** e.g., "dark warehouse interior", "rainy street at night", "white whiteboard".
- **Spatial Compositions:** e.g., "two people sitting at a table", "a truck next to a building".

### What Amon Hen does not match
- **Fine-grained Actions over Time:** Single-frame CLIP representations do not capture temporal sequence dependencies like "a person entering and then immediately leaving the room".
- **Complex Causal Reasoning:** Queries requiring narrative comprehension across extended scene cuts.

---

## Supported Platforms

- **Linux (x86_64 / ARM64):** Supported (CPU execution via ONNX Runtime).
- **macOS (Apple Silicon M-series / Intel):** Supported (CPU execution via ONNX Runtime).
- **Windows (x86_64):** Supported (CPU execution via ONNX Runtime).

---

## Roadmap & Future Milestones

- [x] **v0.1.0 (Core Release):** CPU-native MobileCLIP2 ONNX inference, SQLite vector store, 3-gate adaptive sampler, segment merging, and interactive TUI.
- [ ] **Lossless Video Moment Exporter (`amon-hen cut`):** Instant sub-second video clip extraction using FFmpeg stream copying without re-encoding.
- [ ] **Multi-Model Support:** Distribution and CLI support for larger `MobileCLIP2-S2` models and custom ONNX weights.
- [ ] **Spoken Audio Search:** Whisper ONNX transcription with SQLite FTS5 for hybrid dialogue and visual search.
- [ ] **Local Web UI (`amon-hen serve`):** Browser-based visual video scrubber and timeline heatmap.

See [ROADMAP.md](docs/ROADMAP.md) for full milestone details and contribution guides.

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code style guidelines, and pull request workflows.

Please also read and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).


---

## Security

To report security issues or vulnerabilities, please review our [Security Policy](SECURITY.md).

---

## License

MIT License. See [LICENSE](LICENSE) for details.

