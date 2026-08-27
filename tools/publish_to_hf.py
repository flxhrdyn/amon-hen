from __future__ import annotations

import os
from pathlib import Path


def generate_model_card(model_variant: str, min_cosine: float, latency_ms: float) -> str:
    """Generate a markdown Model Card for Hugging Face repository."""
    return f"""---
language: en
tags:
- clip
- vision
- video-retrieval
- onnx
- cpu-optimized
- edge-ai
- amon-hen
license: mit
---

# {model_variant} (ONNX CPU & Edge Optimized)

Official ONNX weights and quantized models for [{model_variant}](https://github.com/flxhrdyn/amon-hen),
designed for CPU-only execution and edge devices without discrete GPUs.

## Benchmarks & Numerical Parity
* **Architecture:** MobileCLIP2 FastViT Backbone
* **Input Resolution:** 256x256
* **Embedding Dimension:** 512
* **PyTorch Numerical Parity:** Cosine Similarity $\\ge {min_cosine:.4f}$
* **Average CPU Latency:** ~{latency_ms:.1f}ms per frame on standard x86/ARM CPU

## Usage with Amon Hen
```bash
amon-hen index ~/videos/ --sampler adaptive
```
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
