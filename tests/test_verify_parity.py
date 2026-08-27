from __future__ import annotations

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
    rng = np.random.default_rng(seed=42)
    v1 = rng.standard_normal((10, 512), dtype=np.float32)
    v2 = rng.standard_normal((10, 512), dtype=np.float32)
    passed, min_cos, _ = verify_numerical_parity(v1, v2, min_cosine=0.9995)
    assert passed is False
    assert min_cos < 0.9995


def test_verify_numerical_parity_handles_unnormalized_vectors():
    rng = np.random.default_rng(seed=123)
    v1 = rng.standard_normal((10, 512), dtype=np.float32) * 50.0
    # Add tiny perturbation
    v2 = v1 + rng.standard_normal((10, 512), dtype=np.float32) * 1e-4
    passed, min_cos, max_err = verify_numerical_parity(v1, v2, min_cosine=0.9995)
    assert passed is True
    assert min_cos >= 0.9995
    assert max_err < 1e-2


def test_verify_numerical_parity_handles_1d_vectors():
    rng = np.random.default_rng(seed=42)
    v1 = rng.standard_normal(512, dtype=np.float32)
    v2 = v1.copy()
    passed, min_cos, max_err = verify_numerical_parity(v1, v2, min_cosine=0.9995)
    assert passed is True
    assert min_cos > 0.9999
    assert max_err < 1e-5


def test_verify_numerical_parity_raises_on_shape_mismatch():
    v1 = np.ones((5, 512), dtype=np.float32)
    v2 = np.ones((6, 512), dtype=np.float32)
    with pytest.raises(ValueError, match="Shape mismatch"):
        verify_numerical_parity(v1, v2)
