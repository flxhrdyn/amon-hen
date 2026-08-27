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
- text-embeddings
- multimodal
- onnx
- cpu-optimized
- quantization
- int8
- edge-ai
- mobileclip
- fastvit
- amon-hen
pipeline_tag: feature-extraction
---

<div align="center">

<h1 align="center">{variant_name} (ONNX & INT8 Quantized)</h1>

<p align="center">
  <b>Lightweight, CPU-native vision-language embedding model based on Apple's MobileCLIP2 architecture.</b><br>
  <i>Optimized with ONNX Runtime and INT8 dynamic quantization for efficient, zero-GPU inference on laptops, mobile devices, and edge systems.</i>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://onnxruntime.ai/"><img src="https://img.shields.io/badge/Runtime-ONNX%201.18%2B-blueviolet.svg" alt="ONNX Runtime"></a>
  <img src="https://img.shields.io/badge/Target-100%25%20CPU%20%26%20Edge-brightgreen.svg" alt="Pure CPU">
  <img src="https://img.shields.io/badge/Size-105MB%20(Hybrid)-orange.svg" alt="Model Size">
</p>

</div>

---

## Model Overview

`{model_variant}` is a standalone ONNX export and INT8 quantized distribution of Apple's **MobileCLIP2-S0** architecture. This repository provides pre-converted ONNX weights and quantized variants to enable drop-in, zero-dependency deployment with `onnxruntime` across Python, C++, Rust, and mobile/WASM runtimes.

### Key Specifications:
* **Architecture:** Hybrid FastViT vision backbone (approx. 12M parameters) + Lightweight Transformer text encoder (approx. 15M parameters)
* **Input Image Resolution:** 256 x 256 RGB (shortest-edge resize + center crop, ImageNet normalized)
* **Embedding Dimension:** 512 (L2-normalized unit vectors)
* **Context Length:** 77 tokens
* **Total Parameters:** approx. 27M

---

## Model Artifacts & Formats

| File | Precision | File Size | Description |
| :--- | :--- | :--- | :--- |
| `vision_model.onnx` | **FP32** | 43.4 MB | FastViT vision backbone (optimal for CPU execution) |
| `vision_model_quantized.onnx` | **INT8** | 11.3 MB | Dynamic INT8 quantized vision model |
| `text_model.onnx` | **FP32** | 242.3 MB | Full-precision text encoder |
| `text_model_quantized.onnx` | **INT8** | 61.3 MB | Dynamic INT8 quantized text encoder (2.09x faster) |
| `tokenizer.json` | Hugging Face Fast | 2.1 MB | Standalone CLIP BPE tokenizer |

---

## Benchmarks & Quantization Profile

Evaluated on standard x86-64 / ARM64 CPU environments using `onnxruntime` (single-query batch=1, 4 threads):

| Component | FP32 Size | INT8 Size | Size Reduction | Latency (FP32 -> INT8) | Cosine Fidelity | Recommended Mode |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Text Encoder** | 242.3 MB | 61.3 MB | **-74.7%** | 21.6 ms -> **10.3 ms** (2.09x speedup) | 0.9556 | **INT8** |
| **Vision Backbone** | 43.4 MB | 11.3 MB | **-74.0%** | **111.8 ms** -> 1,393.1 ms | 0.2252 (dynamic) | **FP32** |
| **Complete System** | **285.7 MB** | **72.7 MB** | **-74.6%** | **Hybrid: 122 ms total** | >= {min_cosine:.4f} (FP32) | **Hybrid (FP32 Vision + INT8 Text: 105 MB)** |

### Quantization Findings:
1. **Text Transformer:** Quantizes exceptionally well with dynamic INT8 — reducing size by 75% and doubling CPU inference speed while preserving 0.955+ cosine parity.
2. **FastViT Vision:** Dynamic INT8 quantization adds per-layer conversion overhead to depthwise convolutions on CPU. For CPU deployment without dedicated VNNI/NPU calibration, **FP32 vision + INT8 text** delivers the optimal balance of speed (122 ms total latency), accuracy, and small memory footprint (105 MB total).
3. **Parity:** FP32 ONNX outputs maintain cosine similarity >= {min_cosine:.4f} against original PyTorch weights.
4. **Frame Embedding Latency:** {latency_ms:.1f} ms per frame on CPU.


---

## Quickstart

Run standalone inference with `onnxruntime` and `tokenizers` without PyTorch:

```bash
pip install onnxruntime numpy tokenizers pillow
```

```python
import numpy as np
import onnxruntime as ort
from PIL import Image
from tokenizers import Tokenizer

# 1. Load ONNX sessions (Hybrid: FP32 Vision + INT8 Text)
vis_sess = ort.InferenceSession("vision_model.onnx", providers=["CPUExecutionProvider"])
txt_sess = ort.InferenceSession("text_model_quantized.onnx", providers=["CPUExecutionProvider"])
tokenizer = Tokenizer.from_file("tokenizer.json")

# 2. Preprocess & encode image
def preprocess_image(image_path: str) -> np.ndarray:
    img = Image.open(image_path).convert("RGB")
    # Resize shortest edge to 256, center crop 256x256
    w, h = img.size
    scale = 256.0 / min(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
    w, h = img.size
    left = (w - 256) // 2
    top = (h - 256) // 2
    img = img.crop((left, top, left + 256, top + 256))
    
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
    std = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
    arr = (arr - mean) / std
    arr = arr.transpose(2, 0, 1)[np.newaxis, ...]
    return arr.astype(np.float32)

pixel_values = preprocess_image("sample.jpg")
input_name = vis_sess.get_inputs()[0].name
img_emb = vis_sess.run(None, {{input_name: pixel_values}})[0]
img_emb /= np.linalg.norm(img_emb, axis=-1, keepdims=True)

# 3. Preprocess & encode text
query = "a photo of a golden retriever playing in grass"
encoded = tokenizer.encode(query)
tokens = np.array([encoded.ids[:77] + [0] * (77 - len(encoded.ids[:77]))], dtype=np.int64)
txt_input_name = txt_sess.get_inputs()[0].name
txt_emb = txt_sess.run(None, {{txt_input_name: tokens}})[0]
txt_emb /= np.linalg.norm(txt_emb, axis=-1, keepdims=True)

# 4. Compute cosine similarity
similarity = float(np.dot(img_emb[0], txt_emb[0]))
print(f"Cosine Similarity: {{similarity:.4f}}")
```

---

## License & Attribution

* Original model architecture and weights by Apple Inc. under Apple Sample Code / MIT license.
* ONNX conversion and quantization maintained by [@felixhrdyn](https://huggingface.co/felixhrdyn).
* Used in applications such as [Amon Hen](https://github.com/flxhrdyn/amon-hen) for CPU-native semantic search.
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
