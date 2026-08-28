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


_RESOLVED: dict[str, Path] = {}


def ensure_model(spec: ModelSpec) -> Path:
    """Download the model files on first use and return the local directory.

    The result is memoised: resolving a repo costs a round-trip to the
    Hub, and the text encoder would otherwise pay it on every query.
    """
    if spec.repo_id in _RESOLVED:
        return _RESOLVED[spec.repo_id]

    import os

    from huggingface_hub import snapshot_download

    auth_token = os.getenv("HF_TOKEN")
    if not auth_token:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("HF_TOKEN="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        auth_token = val
                        break

    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    location = Path(
        snapshot_download(
            spec.repo_id,
            cache_dir=str(MODEL_CACHE),
            token=auth_token,
            allow_patterns=[spec.vision_file, spec.text_file, spec.tokenizer_file],
        )
    )
    _RESOLVED[spec.repo_id] = location
    return location


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
        self._factory = session_factory or (lambda s: _make_session(s, s.vision_file))
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self._factory(self.spec)
        return self._session

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        # MobileCLIP2's preprocessor_config.json asks for a shortest-edge
        # resize followed by a centre crop. Resizing straight to a square
        # instead squashes the aspect ratio of every video frame, which
        # shifts the embedding by roughly 0.03 cosine on a 16:9 source -
        # the same order as the gap between a good and a mediocre match.
        size = self.spec.image_size
        pil = Image.fromarray(image).convert("RGB")

        width, height = pil.size
        scale = size / min(width, height)
        pil = pil.resize(
            (max(size, round(width * scale)), max(size, round(height * scale))),
            Image.BICUBIC,
        )

        width, height = pil.size
        left, top = (width - size) // 2, (height - size) // 2
        pil = pil.crop((left, top, left + size, top + size))

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
        self._loaded_tokenizer = None
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self._factory(self.spec)
        return self._session

    def _load_tokenizer(self):
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(ensure_model(self.spec) / self.spec.tokenizer_file))
        tokenizer.enable_padding(length=77)
        tokenizer.enable_truncation(max_length=77)
        return tokenizer

    def _tokenize(self, text: str) -> np.ndarray:
        if self._tokenizer is not None:
            return self._tokenizer(text)
        # Built once and kept: rebuilding it per query dominated search
        # latency, at well over a second a call.
        if self._loaded_tokenizer is None:
            self._loaded_tokenizer = self._load_tokenizer()
        ids = self._loaded_tokenizer.encode(text).ids
        return np.asarray([ids], dtype=np.int64)

    def embed(self, text: str) -> np.ndarray:
        tokens = self._tokenize(text)
        session = self.session
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        raw = session.run([output_name], {input_name: tokens})[0]
        return _normalise(np.asarray(raw, dtype=np.float32))[0]
