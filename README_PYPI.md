# Amon Hen

> *"From the Seat of Seeing, no moment remains hidden."*

A fast, lightweight CLI and Python library for natural language video moment retrieval on local CPU. Runs entirely on CPU without discrete GPUs, background daemons, or cloud dependencies.

[![PyPI](https://img.shields.io/pypi/v/amon-hen?color=blue)](https://pypi.org/project/amon-hen/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## Key Highlights

* **100% CPU Execution:** Powered by Apple's MobileCLIP2 architecture and ONNX Runtime.
* **Low Footprint:** Hybrid FP32-vision + INT8-quantized text pipeline (approx. 105 MB RAM).
* **Zero Infrastructure:** Embedded vector database via SQLite and `sqlite-vec` (single `.db` file).
* **High Throughput:** 3-gate adaptive motion sampler achieving 4.8x to 18.5x realtime indexing speed.
* **Temporal Grouping:** Merges consecutive matching frames into start-end timestamp intervals.

---

## Installation

```bash
# Recommended via uv
uv tool install amon-hen

# Or via pipx
pipx install amon-hen

# Or standard pip
pip install amon-hen
```

---

## Quickstart

### 1. Interactive Terminal UI
Run `amon-hen` without arguments to launch the interactive prompt:

```bash
amon-hen
```

### 2. Index Videos
```bash
# Index a video or entire folder with adaptive motion sampling
amon-hen index /path/to/videos/ --sampler adaptive
```

### 3. Search Moments
```bash
# Search using natural language
amon-hen search "a person holding an umbrella"
```

---

## Python API

```python
from amonhen.store import Store
from amonhen.model_registry import get_model
from amonhen.encode import TextEncoder
from amonhen.pipeline import search

# 1. Connect to index
store = Store("index.db", embed_dim=512)

# 2. Load CPU-optimized text encoder
model = get_model("mobileclip2-s0").download()
text_encoder = TextEncoder(model.text_model_path, model.tokenizer_path)

# 3. Retrieve matching video segments
results = search("red sports car turning", store=store, text_encoder=text_encoder)
for seg in results:
    print(f"{seg.video_path}: {seg.start_ms / 1000.0:.1f}s - {seg.end_ms / 1000.0:.1f}s (score: {seg.score:.3f})")
```

---

## Resources & Links

* **GitHub Repository:** [https://github.com/flxhrdyn/amon-hen](https://github.com/flxhrdyn/amon-hen)
* **CLI User Manual:** [https://github.com/flxhrdyn/amon-hen/blob/main/docs/CLI_GUIDE.md](https://github.com/flxhrdyn/amon-hen/blob/main/docs/CLI_GUIDE.md)
* **Python API Documentation:** [https://github.com/flxhrdyn/amon-hen/blob/main/docs/PYTHON_API.md](https://github.com/flxhrdyn/amon-hen/blob/main/docs/PYTHON_API.md)
* **Project Roadmap:** [https://github.com/flxhrdyn/amon-hen/blob/main/docs/ROADMAP.md](https://github.com/flxhrdyn/amon-hen/blob/main/docs/ROADMAP.md)
* **Hugging Face Model Hub:** [https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx)
* **License:** MIT License
