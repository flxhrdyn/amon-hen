# Official ONNX Export, CPU/Edge Quantization & Hugging Face Distribution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust, standalone pipeline to convert Apple MobileCLIP models to ONNX, quantize for pure CPU/Edge devices, verify numerical parity, and distribute via official Hugging Face repositories (`flxhrdyn/mobileclip2-s0-onnx` and `flxhrdyn/mobileclip2-s2-onnx`).

**Architecture:** Standalone Python tooling under `tools/` with modular responsibilities: export (`tools/export_onnx.py`), quantization (`tools/quantize_onnx.py`), parity validation (`tools/verify_parity.py`), and publishing (`tools/publish_to_hf.py`), with core integration in `src/amonhen/model_registry.py`.

**Tech Stack:** PyTorch, ONNX, ONNX Runtime (`onnxruntime.quantization`), OpenCLIP/MobileCLIP, `huggingface_hub`, pytest.

## Global Constraints
- Target Hugging Face repositories: `flxhrdyn/mobileclip2-s0-onnx` & `flxhrdyn/mobileclip2-s2-onnx`.
- Pure CPU execution (0% GPU/CUDA requirements).
- Export & quantization memory footprint $< 1.5\text{ GB}$ RAM.
- Numerical Parity Threshold: Cosine similarity $\ge 0.9995$ on synthetic/real image & text embeddings.
- Zero breaking changes to existing `amonhen` core search and storage APIs.

---

### Task 1: Standalone ONNX Model Exporter (`tools/export_onnx.py`)

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/export_onnx.py`
- Test: `tests/test_export_onnx.py`

**Interfaces:**
- Produces: `export_mobileclip_to_onnx(model_variant: str, output_dir: Path, opset: int = 17) -> tuple[Path, Path, Path]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_export_onnx.py
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from tools.export_onnx import export_mobileclip_to_onnx


def test_export_mobileclip_to_onnx_creates_files(tmp_path: Path):
    with patch("tools.export_onnx._load_pytorch_model") as mock_load, \
         patch("tools.export_onnx._export_vision") as mock_vis, \
         patch("tools.export_onnx._export_text") as mock_txt, \
         patch("tools.export_onnx._export_tokenizer") as mock_tok:
        
        mock_load.return_value = MagicMock()
        mock_vis.return_value = tmp_path / "vision_model.onnx"
        mock_txt.return_value = tmp_path / "text_model.onnx"
        mock_tok.return_value = tmp_path / "tokenizer.json"
        
        vis, txt, tok = export_mobileclip_to_onnx("mobileclip2-s0", tmp_path)
        assert vis.name == "vision_model.onnx"
        assert txt.name == "text_model.onnx"
        assert tok.name == "tokenizer.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_onnx.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.export_onnx'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/export_onnx.py
from __future__ import annotations
from pathlib import Path
import torch

def _load_pytorch_model(variant: str):
    import open_clip
    # Loads MobileCLIP architecture checkpoint
    model_name = "MobileCLIP-s0" if "s0" in variant else "MobileCLIP-s2"
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=None)
    model.eval()
    return model

def _export_vision(model, out_path: Path, opset: int = 17) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_input = torch.randn(1, 3, 256, 256, dtype=torch.float32)
    
    class VisionWrapper(torch.nn.Module):
        def __init__(self, visual):
            super().__init__()
            self.visual = visual
        def forward(self, x):
            return self.visual(x)
            
    wrapper = VisionWrapper(model.visual)
    torch.onnx.export(
        wrapper,
        dummy_input,
        str(out_path),
        input_names=["image"],
        output_names=["embedding"],
        dynamic_axes={"image": {0: "batch_size"}, "embedding": {0: "batch_size"}},
        opset_version=opset,
        do_constant_folding=True,
    )
    return out_path

def _export_text(model, out_path: Path, opset: int = 17) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_tokens = torch.zeros(1, 77, dtype=torch.int64)
    
    class TextWrapper(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m
        def forward(self, tokens):
            return self.m.encode_text(tokens, normalize=True)
            
    wrapper = TextWrapper(model)
    torch.onnx.export(
        wrapper,
        dummy_tokens,
        str(out_path),
        input_names=["tokens"],
        output_names=["embedding"],
        dynamic_axes={"tokens": {0: "batch_size"}, "embedding": {0: "batch_size"}},
        opset_version=opset,
        do_constant_folding=True,
    )
    return out_path

def _export_tokenizer(variant: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Writes huggingface tokenizers json
    import json
    cfg = {"version": "1.0", "truncation": {"max_length": 77}, "padding": {"length": 77}}
    out_path.write_text(json.dumps(cfg, indent=2))
    return out_path

def export_mobileclip_to_onnx(model_variant: str, output_dir: Path, opset: int = 17) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model = _load_pytorch_model(model_variant)
    vis = _export_vision(model, output_dir / "vision_model.onnx", opset=opset)
    txt = _export_text(model, output_dir / "text_model.onnx", opset=opset)
    tok = _export_tokenizer(model_variant, output_dir / "tokenizer.json")
    return vis, txt, tok
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_export_onnx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/__init__.py tools/export_onnx.py tests/test_export_onnx.py
git commit -m "feat: add standalone ONNX exporter for MobileCLIP"
```

---

### Task 2: Graph Optimization & CPU/Edge Quantizer (`tools/quantize_onnx.py`)

**Files:**
- Create: `tools/quantize_onnx.py`
- Test: `tests/test_quantize_onnx.py`

**Interfaces:**
- Produces: `quantize_onnx_model(input_onnx_path: Path, output_onnx_path: Path, quant_format: str = "int8") -> Path`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_quantize_onnx.py
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from tools.quantize_onnx import quantize_onnx_model


def test_quantize_onnx_model_executes_dynamic_quant(tmp_path: Path):
    in_model = tmp_path / "model.onnx"
    in_model.write_bytes(b"dummy onnx bytes")
    out_model = tmp_path / "model_quant.onnx"
    
    with patch("onnxruntime.quantization.quantize_dynamic") as mock_quant:
        res = quantize_onnx_model(in_model, out_model, quant_format="int8")
        assert res == out_model
        assert mock_quant.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_quantize_onnx.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.quantize_onnx'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/quantize_onnx.py
from __future__ import annotations
from pathlib import Path
from onnxruntime.quantization import quantize_dynamic, QuantType

def quantize_onnx_model(
    input_onnx_path: Path,
    output_onnx_path: Path,
    quant_format: str = "int8"
) -> Path:
    output_onnx_path.parent.mkdir(parents=True, exist_ok=True)
    quantize_dynamic(
        model_input=str(input_onnx_path),
        model_output=str(output_onnx_path),
        weight_type=QuantType.QInt8 if quant_format.lower() == "int8" else QuantType.QUInt8,
    )
    return output_onnx_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_quantize_onnx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/quantize_onnx.py tests/test_quantize_onnx.py
git commit -m "feat: add CPU/Edge dynamic quantizer for ONNX models"
```

---

### Task 3: Numerical Parity & Cosine Similarity Verifier (`tools/verify_parity.py`)

**Files:**
- Create: `tools/verify_parity.py`
- Test: `tests/test_verify_parity.py`

**Interfaces:**
- Produces: `verify_numerical_parity(pytorch_embeddings: np.ndarray, onnx_embeddings: np.ndarray, min_cosine: float = 0.9995) -> tuple[bool, float, float]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verify_parity.py
import numpy as np
import pytest
from tools.verify_parity import verify_numerical_parity


def test_verify_numerical_parity_passes_identical_vectors():
    v1 = np.random.randn(10, 512).astype(np.float32)
    v1 /= np.linalg.norm(v1, axis=1, keepdims=True)
    v2 = v1.copy()
    passed, min_cos, max_err = verify_numerical_parity(v1, v2, min_cosine=0.9995)
    assert passed is True
    assert min_cos > 0.9999
    assert max_err < 1e-5


def test_verify_numerical_parity_fails_divergent_vectors():
    v1 = np.random.randn(10, 512).astype(np.float32)
    v2 = np.random.randn(10, 512).astype(np.float32)
    passed, min_cos, _ = verify_numerical_parity(v1, v2, min_cosine=0.9995)
    assert passed is False
    assert min_cos < 0.9995
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_verify_parity.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.verify_parity'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/verify_parity.py
from __future__ import annotations
import numpy as np

def verify_numerical_parity(
    pytorch_embeddings: np.ndarray,
    onnx_embeddings: np.ndarray,
    min_cosine: float = 0.9995,
) -> tuple[bool, float, float]:
    """Check cosine similarity and max absolute error between PyTorch and ONNX outputs."""
    p_norm = pytorch_embeddings / np.linalg.norm(pytorch_embeddings, axis=1, keepdims=True)
    o_norm = onnx_embeddings / np.linalg.norm(onnx_embeddings, axis=1, keepdims=True)
    
    cos_sims = np.sum(p_norm * o_norm, axis=1)
    min_cos = float(np.min(cos_sims))
    max_err = float(np.max(np.abs(pytorch_embeddings - onnx_embeddings)))
    
    passed = bool(min_cos >= min_cosine)
    return passed, min_cos, max_err
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_verify_parity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/verify_parity.py tests/test_verify_parity.py
git commit -m "feat: add numerical parity and cosine similarity verifier"
```

---

### Task 4: Hugging Face Packager & Publisher (`tools/publish_to_hf.py`)

**Files:**
- Create: `tools/publish_to_hf.py`
- Test: `tests/test_publish_hf.py`

**Interfaces:**
- Produces: `generate_model_card(model_variant: str, min_cosine: float, latency_ms: float) -> str`
- Produces: `publish_model_package(repo_id: str, package_dir: Path, token: str | None = None) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_publish_hf.py
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from tools.publish_to_hf import generate_model_card, publish_model_package


def test_generate_model_card_contains_metadata():
    card = generate_model_card("mobileclip2-s0", min_cosine=0.9998, latency_ms=25.4)
    assert "mobileclip2-s0" in card
    assert "0.9998" in card
    assert "25.4" in card
    assert "Amon Hen" in card


def test_publish_model_package_calls_hf_api(tmp_path: Path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "README.md").write_text("Model card")
    
    with patch("huggingface_hub.HfApi") as mock_hf:
        mock_api = MagicMock()
        mock_hf.return_value = mock_api
        
        url = publish_model_package("flxhrdyn/mobileclip2-s0-onnx", pkg_dir, token="test_token")
        assert "flxhrdyn/mobileclip2-s0-onnx" in url
        assert mock_api.upload_folder.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_publish_hf.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.publish_to_hf'`

- [ ] **Step 3: Write minimal implementation**

```python
# tools/publish_to_hf.py
from __future__ import annotations
import os
from pathlib import Path
from huggingface_hub import HfApi

def generate_model_card(model_variant: str, min_cosine: float, latency_ms: float) -> str:
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

Official ONNX weights and quantized models for [{model_variant}](https://github.com/flxhrdyn/amon-hen), designed for CPU-only execution and edge devices without discrete GPUs.

## Benchmarks & Numerical Parity
* **Architecture:** MobileCLIP2 FastViT Backbone
* **Input Resolution:** 256x256
* **Embedding Dimension:** 512
* **PyTorch Numerical Parity:** Cosine Similarity $\ge {min_cosine:.4f}$
* **Average CPU Latency:** ~{latency_ms:.1f}ms per frame on standard x86/ARM CPU

## Usage with Amon Hen
```bash
amon-hen index ~/videos/ --sampler adaptive
```
"""

def publish_model_package(repo_id: str, package_dir: Path, token: str | None = None) -> str:
    auth_token = token or os.getenv("HF_TOKEN")
    api = HfApi(token=auth_token)
    api.create_repo(repo_id=repo_id, exist_ok=True, repo_type="model")
    api.upload_folder(
        folder_path=str(package_dir),
        repo_id=repo_id,
        repo_type="model",
        commit_message=f"Release official ONNX artifacts for {repo_id}",
    )
    return f"https://huggingface.co/{repo_id}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_publish_hf.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/publish_to_hf.py tests/test_publish_hf.py
git commit -m "feat: add Hugging Face model packaging and publishing tool"
```

---

### Task 5: Model Registry Update in Core Amon Hen (`src/amonhen/model_registry.py`)

**Files:**
- Modify: `src/amonhen/model_registry.py`
- Test: `tests/test_model_registry.py`

**Interfaces:**
- Consumes: Model registry definitions
- Produces: Verified `flxhrdyn/mobileclip2-s0-onnx` and `flxhrdyn/mobileclip2-s2-onnx` specs

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_model_registry.py
def test_default_models_point_to_official_flxhrdyn_namespace():
    s0 = get_model("mobileclip2-s0")
    assert s0.repo_id == "flxhrdyn/mobileclip2-s0-onnx"
    assert s0.embed_dim == 512
    assert s0.image_size == 256
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_model_registry.py -k "test_default_models_point_to_official_flxhrdyn_namespace" -v`
Expected: FAIL (`AssertionError: assert 'plhery/mobileclip2-onnx' == 'flxhrdyn/mobileclip2-s0-onnx'`)

- [ ] **Step 3: Update `src/amonhen/model_registry.py`**

```python
# In src/amonhen/model_registry.py
MOBILECLIP2_S0 = ModelSpec(
    model_id="mobileclip2-s0",
    repo_id="flxhrdyn/mobileclip2-s0-onnx",
    vision_file="onnx/vision_model.onnx",
    text_file="onnx/text_model.onnx",
    tokenizer_file="tokenizer.json",
    embed_dim=512,
    image_size=256,
)

MOBILECLIP2_S2 = ModelSpec(
    model_id="mobileclip2-s2",
    repo_id="flxhrdyn/mobileclip2-s2-onnx",
    vision_file="onnx/vision_model.onnx",
    text_file="onnx/text_model.onnx",
    tokenizer_file="tokenizer.json",
    embed_dim=512,
    image_size=256,
)

DEFAULT_MODEL = MOBILECLIP2_S0

_REGISTRY = {spec.model_id: spec for spec in (MOBILECLIP2_S0, MOBILECLIP2_S2)}
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run pytest -v`
Expected: ALL 130+ tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/model_registry.py tests/test_model_registry.py
git commit -m "feat: point default model registry to official flxhrdyn Hugging Face repos"
```
