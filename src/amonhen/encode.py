"""ONNX Runtime wrappers around the image and text encoders.

Both encoders take a `session_factory` so tests can substitute a fake
session and exercise preprocessing, batching, and normalisation without
downloading a model.

Embeddings are L2-normalised here rather than at query time, which makes
cosine similarity a plain dot product everywhere downstream.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

from amonhen.model_registry import DEFAULT_MODEL, ModelSpec

MODEL_CACHE = Path.home() / ".amonhen" / "models"

# MobileCLIP2's own preprocessor_config.json specifies mean=[0,0,0],
# std=[1,1,1] - unlike most OpenCLIP models, it does not re-normalise
# beyond scaling pixels to [0, 1]. Using the standard OpenAI CLIP mean/std
# here silently produced near-zero cosine similarities against the real
# model; this was caught by the slow real-model sanity test, not by the
# fake-session unit tests, which is why that test exists.
_MEAN = np.array([0.0, 0.0, 0.0], dtype=np.float32)
_STD = np.array([1.0, 1.0, 1.0], dtype=np.float32)


def ensure_model(spec: ModelSpec) -> Path:
    """Download the model files on first use and return the local directory."""
    from huggingface_hub import snapshot_download

    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    return Path(
        snapshot_download(
            spec.repo_id,
            cache_dir=str(MODEL_CACHE),
            allow_patterns=[spec.vision_file, spec.text_file, spec.tokenizer_file],
        )
    )


def _make_session(spec: ModelSpec, filename: str) -> ort.InferenceSession:
    path = ensure_model(spec) / filename
    return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])


def _normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (vectors / norms).astype(np.float32)


class ImageEncoder:
    def __init__(
        self,
        spec: ModelSpec = DEFAULT_MODEL,
        session_factory: Callable[[ModelSpec], object] | None = None,
    ):
        self.spec = spec
        self._factory = session_factory or (
            lambda s: _make_session(s, s.vision_file)
        )
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self._factory(self.spec)
        return self._session

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        size = self.spec.image_size
        pil = Image.fromarray(image).convert("RGB").resize((size, size), Image.BICUBIC)
        array = np.asarray(pil, dtype=np.float32) / 255.0
        array = (array - _MEAN) / _STD
        return array.transpose(2, 0, 1)

    def embed(self, images: list[np.ndarray]) -> np.ndarray:
        if not images:
            return np.zeros((0, self.spec.embed_dim), dtype=np.float32)

        batch = np.stack([self._preprocess(image) for image in images]).astype(np.float32)
        session = self.session
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        raw = session.run([output_name], {input_name: batch})[0]
        return _normalise(np.asarray(raw, dtype=np.float32))


class TextEncoder:
    def __init__(
        self,
        spec: ModelSpec = DEFAULT_MODEL,
        session_factory: Callable[[ModelSpec], object] | None = None,
        tokenizer: Callable[[str], np.ndarray] | None = None,
    ):
        self.spec = spec
        self._factory = session_factory or (lambda s: _make_session(s, s.text_file))
        self._tokenizer = tokenizer
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self._factory(self.spec)
        return self._session

    def _tokenize(self, text: str) -> np.ndarray:
        if self._tokenizer is not None:
            return self._tokenizer(text)
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(ensure_model(self.spec) / self.spec.tokenizer_file))
        tokenizer.enable_padding(length=77)
        tokenizer.enable_truncation(max_length=77)
        ids = tokenizer.encode(text).ids
        return np.asarray([ids], dtype=np.int64)

    def embed(self, text: str) -> np.ndarray:
        tokens = self._tokenize(text)
        session = self.session
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        raw = session.run([output_name], {input_name: tokens})[0]
        return _normalise(np.asarray(raw, dtype=np.float32))[0]
