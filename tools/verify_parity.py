from __future__ import annotations

import numpy as np


def verify_numerical_parity(
    pytorch_embeddings: np.ndarray,
    onnx_embeddings: np.ndarray,
    min_cosine: float = 0.9995,
) -> tuple[bool, float, float]:
    """Check cosine similarity and max absolute error between PyTorch and ONNX outputs.

    Args:
        pytorch_embeddings: Embeddings produced by PyTorch model (1D or 2D array).
        onnx_embeddings: Embeddings produced by ONNX model (1D or 2D array).
        min_cosine: Minimum acceptable cosine similarity threshold.

    Returns:
        tuple of (passed, min_cosine_similarity, max_absolute_error)
    """
    p = np.asarray(pytorch_embeddings, dtype=np.float32)
    o = np.asarray(onnx_embeddings, dtype=np.float32)

    if p.shape != o.shape:
        raise ValueError(f"Shape mismatch: pytorch {p.shape} vs onnx {o.shape}")

    if p.ndim == 1:
        p = p[np.newaxis, :]
        o = o[np.newaxis, :]
    elif p.ndim != 2:
        raise ValueError(f"Expected 1D or 2D embeddings, got shape {p.shape}")

    p_norm_val = np.linalg.norm(p, axis=1, keepdims=True)
    o_norm_val = np.linalg.norm(o, axis=1, keepdims=True)

    # Avoid division by zero
    p_norm = p / np.maximum(p_norm_val, 1e-12)
    o_norm = o / np.maximum(o_norm_val, 1e-12)

    cos_sims = np.sum(p_norm * o_norm, axis=1)
    cos_sims = np.clip(cos_sims, -1.0, 1.0)

    min_cos = float(np.min(cos_sims))
    max_err = float(np.max(np.abs(p - o)))

    passed = bool(min_cos >= min_cosine)
    return passed, min_cos, max_err
