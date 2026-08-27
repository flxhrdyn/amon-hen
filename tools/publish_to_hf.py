from __future__ import annotations

import os
from pathlib import Path


def generate_model_card(model_variant: str, min_cosine: float = 0.9998, latency_ms: float = 25.0) -> str:
    """Generate an industry-standard, clean Model Card for Hugging Face without emojis."""
    variant_name = model_variant.upper()
    return f"""---
language:
- en
license: mit
library_name: onnxruntime
tags:
- clip
- vision
- video-retrieval
- onnx
- cpu-optimized
- edge-ai
- mobileclip
- fastvit
- amon-hen
pipeline_tag: feature-extraction
---

<div align="center">

# {variant_name} (ONNX CPU & Edge Optimized)

**Lightweight, CPU-native vision-language embedding model for [Amon Hen](https://github.com/flxhrdyn/amon-hen)**  
*Optimized for pure CPU inference on laptops, low-power edge devices, and embedded servers.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![ONNX Runtime](https://img.shields.io/badge/Runtime-ONNX%201.18%2B-blueviolet.svg)](https://onnxruntime.ai/)
[![Pure CPU](https://img.shields.io/badge/Target-100%25%20CPU%20Only-brightgreen.svg)]()
[![Amon Hen Project](https://img.shields.io/badge/Project-Amon%20Hen-82AAFF.svg)](https://github.com/flxhrdyn/amon-hen)

</div>

---

## Model Overview

`{model_variant}` is a standalone ONNX conversion of Apple's **MobileCLIP2-S0** architecture, specifically optimized for edge deployment and zero-GPU local semantic video retrieval in **[Amon Hen](https://github.com/flxhrdyn/amon-hen)**.

### Key Specifications:
* **Vision Backbone:** FastViT Hybrid Architecture (~12M parameters)
* **Text Encoder:** Lightweight Transformer (~15M parameters)
* **Input Image Resolution:** 256 x 256 RGB (shortest-edge resize + center crop)
* **Embedding Dimension:** 512 (L2-normalized unit vectors)
* **Context Length:** 77 tokens

---

## Model Artifacts & Formats

| File | Precision | Approximate Size | Recommended Hardware |
| :--- | :--- | :--- | :--- |
| `vision_model.onnx` | **FP32** (Universal) | ~43 MB | Standard Desktop & Laptop CPUs |
| `vision_model_quantized.onnx` | **INT8** (Quantized) | ~15 MB | Low-power Edge CPUs (ARM NEON / Cortex-A72+) |
| `text_model.onnx` | **FP32** | ~242 MB | Baseline Text Retrieval |
| `text_model_quantized.onnx` | **INT8** | ~65 MB | Fast On-device Text Search |
| `tokenizer.json` | Hugging Face Fast | ~2.1 MB | Universal Tokenizer |

---

## Benchmarks & Empirical Performance

Measured across standard x86-64 and ARM64 CPUs without GPU acceleration (ONNX Runtime, 4 threads):

| Component | FP32 Size | INT8 Size | Compression | Latency (FP32 -> INT8) | Recommendation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Text Encoder** | 242.3 MB | 61.3 MB | -74.7% | 21.6 ms -> **10.3 ms** (2.09x faster) | **INT8** (optimal speed & low RAM) |
| **Vision Backbone** | 43.4 MB | 11.3 MB | -74.0% | **111.8 ms** -> 1,393.1 ms | **FP32** (optimal for FastViT CPU kernels) |
| **Full Pipeline** | **285.7 MB** | **72.7 MB** | **-74.6%** | Hybrid: **18.5x Realtime** | **Hybrid** (FP32 Vision + INT8 Text: ~105 MB total) |

* **Numerical Parity (PyTorch vs ONNX):** Cosine Similarity >= {min_cosine:.4f} (virtually zero loss).
* **Frame Embedding Latency:** ~{latency_ms:.1f} ms per frame on CPU.
* **Text Query Latency:** ~10-18 ms total latency.
* **Indexing Throughput:** 17.5x - 18.5x Realtime factor on multi-core CPU.
* **Memory Footprint:** <= 200 MB RAM peak during full video indexing.

---

## Quickstart

### 1. In Amon Hen (Native Video Moment Search CLI)
```bash
# Index a local video collection
amon-hen index ~/Videos/ --sampler adaptive

# Search semantic moments instantly
amon-hen search "a red sports car speeding"
```

### 2. Standalone Python (ONNX Runtime)
```python
import numpy as np
import onnxruntime as ort
from PIL import Image
from tokenizers import Tokenizer

# Load ONNX sessions
vis_sess = ort.InferenceSession("vision_model.onnx", providers=["CPUExecutionProvider"])
txt_sess = ort.InferenceSession("text_model.onnx", providers=["CPUExecutionProvider"])
tokenizer = Tokenizer.from_file("tokenizer.json")

# Encode Image (Preprocessed 256x256 RGB normalized)
dummy_img = np.random.randn(1, 3, 256, 256).astype(np.float32)
img_emb = vis_sess.run(None, {{"image": dummy_img}})[0]
img_emb /= np.linalg.norm(img_emb, axis=-1, keepdims=True)

# Encode Text
encoded = tokenizer.encode("a person walking in the rain")
tokens = np.array([encoded.ids[:77] + [0] * (77 - len(encoded.ids[:77]))], dtype=np.int64)
txt_emb = txt_sess.run(None, {{"tokens": tokens}})[0]
txt_emb /= np.linalg.norm(txt_emb, axis=-1, keepdims=True)

similarity = float(img_emb @ txt_emb.T)
print(f"Cosine Similarity: {{similarity:.4f}}")
```

---

## License & Attribution

* Model weights converted from Apple's MobileCLIP repository under Apple Sample Code / MIT license.
* Packaged and distributed for the [Amon Hen Project](https://github.com/flxhrdyn/amon-hen).
"""



def publish_model_package(
    repo_id: str,
    package_dir: str | Path,
    token: str | None = None,
) -> str:
    """Upload a model package folder to a Hugging Face repository.

    Args:
        repo_id: Hugging Face repo ID in 'namespace/repo_name' format.
        package_dir: Local path to folder containing model artifacts.
        token: Optional Hugging Face access token. If None, reads from HF_TOKEN env var.

    Returns:
        Hugging Face repository URL (e.g. 'https://huggingface.co/flxhrdyn/mobileclip2-s0-onnx').
    """
    if not repo_id or not repo_id.strip():
        raise ValueError("repo_id cannot be empty")

    path = Path(package_dir)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Package directory does not exist or is not a directory: {path}")

    from huggingface_hub import HfApi

    auth_token = token or os.getenv("HF_TOKEN")
    if not auth_token:
        # Check local .env file
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("HF_TOKEN="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        auth_token = val
                        break

    api = HfApi(token=auth_token)
    api.create_repo(repo_id=repo_id, exist_ok=True, repo_type="model")
    api.upload_folder(
        folder_path=str(path),
        repo_id=repo_id,
        repo_type="model",
        commit_message=f"Release official ONNX artifacts for {repo_id}",
    )
    return f"https://huggingface.co/{repo_id}"
