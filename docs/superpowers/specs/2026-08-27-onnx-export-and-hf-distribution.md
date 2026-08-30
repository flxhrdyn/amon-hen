# Design Spec: Official ONNX Export, CPU/Edge Quantization & Hugging Face Distribution

**Date:** 2026-08-27  
**Status:** Approved  
**Target:** Amon Hen (`flxhrdyn/amon-hen`)  
**Target Hugging Face Namespaces:** `flxhrdyn/mobileclip2-s0-onnx` & `flxhrdyn/mobileclip2-s2-onnx`

---

## 1. Overview & Motivation

Amon Hen relies on lightweight vision-language embeddings to perform natural language moment retrieval across video archives on pure CPU without discrete GPUs.

Currently, the default model registry points to a third-party community Hugging Face repository (`plhery/mobileclip2-onnx`). While functional, relying on third-party model hosting introduces:
1. **Supply Chain Risk:** External deletion, silent weight modification, or repository corruption could break downstream user installations.
2. **Lack of Precision Control:** No official multi-precision variants (FP32 baseline vs INT8/FP8 optimized for low-power edge CPUs like ARM Cortex-A72/A76, Apple Silicon, and x86 mini-PCs).
3. **Missing Model Card & Provenance:** No official benchmarks, numerical parity verification reports, or direct linkage to the Amon Hen project.

This specification defines the pipeline to:
1. Convert official Apple MobileCLIP (`apple/ml-mobileclip`) PyTorch checkpoints to clean, standalone ONNX models.
2. Optimize and quantize the ONNX computational graphs for ultra-low latency on pure CPU / Edge devices.
3. Validate numerical parity ($>0.999$ cosine similarity) between PyTorch source and exported ONNX models.
4. Package and publish official repositories on Hugging Face (`flxhrdyn/mobileclip2-s0-onnx` and `flxhrdyn/mobileclip2-s2-onnx`) with comprehensive Model Cards and preprocessors.
5. Update Amon Hen's internal model registry to default to the official repositories.

---

## 2. Architecture & Precision Strategy

### 2.1 Model Variants
* **`mobileclip2-s0` (Primary Edge Target):**
  * Architecture: FastViT-based hybrid vision encoder + lightweight Transformer text encoder.
  * Parameters: $\approx 12\text{M}$ vision, $\approx 15\text{M}$ text.
  * Embedding Dimension: $512$.
  * Input Resolution: $256 \times 256$.
  * Target Hardware: Low-power Edge CPUs (Raspberry Pi 4/5, thin clients, low-spec VPS, standard laptops).
* **`mobileclip2-s2` (High-Accuracy Edge Target):**
  * Architecture: Deeper FastViT vision backbone for higher semantic retrieval precision.
  * Embedding Dimension: $512$.
  * Input Resolution: $256 \times 256$.
  * Target Hardware: Multi-core desktop/laptop CPUs and edge servers.

### 2.2 Precision Artifacts per Hugging Face Repository
Each model repository (e.g. `flxhrdyn/mobileclip2-s0-onnx`) will contain:
* `onnx/vision_model.onnx` — **FP32 Baseline** ($\approx 40\text{ MB}$), $100\%$ universal CPU compatibility, zero quantization error.
* `onnx/vision_model_quantized.onnx` — **INT8/FP8 Quantized** ($\approx 15\text{ MB}$), optimized with ONNX Runtime static/dynamic quantization for ARM NEON and x86 AVX2.
* `onnx/text_model.onnx` — **FP32 Text Encoder** ($\approx 35\text{ MB}$).
* `onnx/text_model_quantized.onnx` — **Quantized Text Encoder** ($\approx 12\text{ MB}$).
* `tokenizer.json` & `tokenizer_config.json` — Hugging Face Tokenizers fast serialization format.
* `preprocessor_config.json` — Preprocessing spec (RGB, resize $256 \times 256$, mean/std normalizer).
* `README.md` — Complete Model Card with hardware benchmarks, latency metrics, and usage code.

---

## 3. Component Design

### 3.1 Exporter Script (`tools/export_onnx.py`)
A standalone CLI utility that orchestrates the conversion:
1. **PyTorch Weight Ingestion:**
   * Uses `open_clip` / official Apple MobileCLIP checkpoint loader.
   * Extracts vision model backbone and text projection heads.
2. **ONNX Export (`torch.onnx.export`):**
   * Vision model input shape: `(batch_size, 3, 256, 256)`, dynamic axes on `batch_size`.
   * Text model input shape: `(batch_size, 77)` int64 token IDs, dynamic axes on `batch_size`.
   * Opset version: `17` (ensures modern layer normalization and attention operator compatibility).
3. **Graph Optimization:**
   * Constant folding, redundant reshape elimination, and operator fusion via `onnxruntime.transformers.optimizer` or `onnxsim`.
4. **Quantization Engine:**
   * Applies `onnxruntime.quantization.quantize_dynamic` / `quantize_static` (asymmetric/symmetric INT8 for MatMul and Conv layers where beneficial).

### 3.2 Parity & Integrity Verification (`tools/verify_parity.py`)
Before any model upload, automated numerical validation is executed:
1. Runs $N=50$ synthetic and real image inputs through both PyTorch model and exported ONNX models.
2. Runs $N=50$ text prompts through PyTorch text encoder and exported ONNX text model.
3. Computes Cosine Similarity $\cos(\mathbf{e}_{\text{pytorch}}, \mathbf{e}_{\text{onnx}})$:
   * **Passing Criteria:** Cosine similarity $\ge 0.9995$ on all samples.
   * **Maximum Absolute Error:** $|e_{\text{pytorch}} - e_{\text{onnx}}| < 1\times 10^{-3}$.

### 3.3 Publisher Engine (`tools/publish_to_hf.py`)
Uses `huggingface_hub.HfApi`:
1. Authenticates via environment variable `HF_TOKEN`.
2. Creates or connects to repository `flxhrdyn/mobileclip2-s0-onnx` (and `-s2-onnx`).
3. Uploads directory contents with automated commit messages and tags.
4. Generates structured `README.md` containing Hugging Face metadata tags:
   * `tags: [clip, vision, video-retrieval, onnx, cpu-optimized, edge-ai]`
   * `license: mit` / `apple-sample-code`

---

## 4. Integration with Amon Hen Core

In `src/amonhen/model_registry.py`:
```python
MOBILECLIP2_S0 = ModelSpec(
    model_id="mobileclip2-s0",
    repo_id="flxhrdyn/mobileclip2-s0-onnx",
    vision_file="onnx/vision_model.onnx",
    text_file="onnx/text_model.onnx",
    tokenizer_file="tokenizer.json",
    embed_dim=512,
    image_size=256,
    preprocess_version=2,
)

MOBILECLIP2_S2 = ModelSpec(
    model_id="mobileclip2-s2",
    repo_id="flxhrdyn/mobileclip2-s2-onnx",
    vision_file="onnx/vision_model.onnx",
    text_file="onnx/text_model.onnx",
    tokenizer_file="tokenizer.json",
    embed_dim=512,
    image_size=256,
    preprocess_version=2,
)
```

In `src/amonhen/encode.py`:
* Automatically downloads and caches from the official `flxhrdyn/*` repository.
* Verifies cached hash to prevent tamper or corrupt downloads.

---

## 5. Non-Functional Requirements & Constraints

1. **Pure CPU Execution:** Zero CUDA/GPU dependencies required for export, validation, or inference.
2. **Minimal Build Memory Footprint:** Export process requires $< 1.5\text{ GB}$ system RAM.
3. **Zero Breaking Changes:** Existing vector stores and API signatures in Amon Hen remain $100\%$ backward-compatible.
4. **Standalone Tooling:** Export scripts live in `tools/` and do not bloat the production runtime package of `amonhen`.
