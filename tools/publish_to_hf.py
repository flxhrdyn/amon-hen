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

**Lightweight, CPU-native vision-language embedding model based on Apple's MobileCLIP2 architecture.**  
*Optimized with ONNX Runtime and INT8 dynamic quantization for efficient, zero-GPU inference on laptops, mobile devices, and edge systems.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) [![ONNX Runtime](https://img.shields.io/badge/Runtime-ONNX%201.18%2B-blueviolet.svg)](https://onnxruntime.ai/) [![Pure CPU](https://img.shields.io/badge/Target-100%25%20CPU%20%26%20Edge-brightgreen.svg)](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx) [![Model Size](https://img.shields.io/badge/Size-105MB%20(Hybrid)-orange.svg)](https://huggingface.co/felixhrdyn/mobileclip2-s0-onnx)

</div>

---

## Model Overview

`{model_variant}` provides standalone ONNX weights and INT8 dynamic quantized variants of Apple's **MobileCLIP2-S0** architecture, optimized for zero-GPU inference with `onnxruntime` across Python, C++, Rust, and mobile/WASM runtimes.

* **Architecture:** FastViT hybrid vision backbone (~12M params) + Transformer text encoder (~15M params)
* **Image Input:** 256 x 256 RGB (shortest-edge resize + center crop, ImageNet normalized)
* **Embedding Output:** 512 dimensions (L2-normalized unit vectors)
* **Context Length:** 77 tokens
* **Total Parameters:** approx. 27M

---

## Deployment Profiles & Benchmarks

Choose the configuration that best matches your target hardware constraints:

| Profile | Vision Model | Text Model | Total Size | Vision Latency | Text Latency | Recommended For |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **Hybrid (Recommended)** | `vision_model.onnx` (FP32) | `text_model_quantized.onnx` (INT8) | **105 MB** | **112 ms** | **10 ms** | Standard CPU desktops, laptops, and servers (fastest indexing) |
| **Full INT8** | `vision_model_quantized.onnx` (INT8) | `text_model_quantized.onnx` (INT8) | **72.7 MB** | 1,393 ms | **10 ms** | Extreme memory/storage constraints, IoT, and WASM |
| **Full FP32** | `vision_model.onnx` (FP32) | `text_model.onnx` (FP32) | **285.7 MB** | **112 ms** | 22 ms | Full precision baseline & exact PyTorch parity verification |

* **Text Transformer:** Quantizes with dynamic INT8 — cutting model size by 75% while accelerating CPU text encoding by **2.09x** with high fidelity (0.9556 cosine similarity).
* **FastViT Vision:** Dynamic INT8 on CPU introduces conversion overhead on depthwise convolutions. Thus, **FP32 vision + INT8 text (Hybrid: 105 MB)** delivers the best balance of speed (122 ms total latency), accuracy, and memory footprint.
* **Numerical Parity:** FP32 ONNX outputs maintain cosine similarity >= {min_cosine:.4f} against original PyTorch weights.
* **Frame Embedding Latency:** {latency_ms:.1f} ms per frame on CPU.

---

## Available Model Artifacts

| File | Precision | File Size | Description |
| :--- | :--- | :--- | :--- |
| `vision_model.onnx` | **FP32** | 43.4 MB | FastViT vision backbone (optimal for CPU execution) |
| `text_model_quantized.onnx` | **INT8** | 61.3 MB | Dynamic INT8 quantized text encoder (2.09x faster on CPU) |
| `vision_model_quantized.onnx` | **INT8** | 11.3 MB | Dynamic INT8 quantized FastViT vision model |
| `text_model.onnx` | **FP32** | 242.3 MB | Full-precision text encoder |
| `tokenizer.json` | Hugging Face Fast | 2.1 MB | Standalone CLIP BPE tokenizer |

---

## Quickstart

### 1. Download Files
Download only the files you need using `huggingface_hub`:

```python
from huggingface_hub import hf_hub_download

# Download recommended Hybrid configuration (105 MB total)
vision_path = hf_hub_download(repo_id="felixhrdyn/mobileclip2-s0-onnx", filename="vision_model.onnx")
text_path = hf_hub_download(repo_id="felixhrdyn/mobileclip2-s0-onnx", filename="text_model_quantized.onnx")
tokenizer_path = hf_hub_download(repo_id="felixhrdyn/mobileclip2-s0-onnx", filename="tokenizer.json")
```

### 2. Standalone Inference with ONNX Runtime

```bash
pip install onnxruntime numpy tokenizers pillow huggingface-hub
```

```python
import numpy as np
import onnxruntime as ort
from PIL import Image
from tokenizers import Tokenizer

# 1. Load ONNX sessions (Hybrid configuration)
vis_sess = ort.InferenceSession("vision_model.onnx", providers=["CPUExecutionProvider"])
txt_sess = ort.InferenceSession("text_model_quantized.onnx", providers=["CPUExecutionProvider"])
tokenizer = Tokenizer.from_file("tokenizer.json")

# 2. Preprocess & encode image
def preprocess_image(image_path: str) -> np.ndarray:
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    scale = 256.0 / min(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
    w, h = img.size
    img = img.crop(((w - 256) // 2, (h - 256) // 2, (w - 256) // 2 + 256, (h - 256) // 2 + 256))
    
    arr = (np.array(img, dtype=np.float32) / 255.0 - [0.48145466, 0.4578275, 0.40821073]) / [0.26862954, 0.26130258, 0.27577711]
    return arr.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)

pixel_values = preprocess_image("sample.jpg")
input_name = vis_sess.get_inputs()[0].name
img_emb = vis_sess.run(None, {{input_name: pixel_values}})[0]
img_emb /= np.linalg.norm(img_emb, axis=-1, keepdims=True)

# 3. Preprocess & encode text
encoded = tokenizer.encode("a photo of a golden retriever playing in grass")
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
