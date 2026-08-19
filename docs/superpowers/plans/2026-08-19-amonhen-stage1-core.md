# AmonHen Stage 1 (Core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the working core of AmonHen — index a video file into a local SQLite vector database and retrieve frame timestamps by text query, entirely on CPU.

**Architecture:** A one-directional pipeline. `decode` streams frames out of ffmpeg, `sample` decides which frames are worth keeping, `encode` turns them into MobileCLIP2 embeddings via ONNX Runtime, and `store` persists them into `sqlite-vec`. `pipeline` is the only module that knows the order of those steps; `cli` is a thin layer over `pipeline`. Lower-layer modules never import each other.

**Tech Stack:** Python 3.13, ONNX Runtime, MobileCLIP2 (ONNX), sqlite-vec, NumPy, Pillow, imageio-ffmpeg, Typer, pytest, ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-19-amonhen-design.md`

## Global Constraints

- Python 3.11 or newer. Development target is 3.13.
- Tested platforms are Windows x86 and Linux x86 only. Never write claims about Raspberry Pi, Jetson, or edge devices anywhere in code, docstrings, or docs.
- No GPU. ONNX Runtime uses `CPUExecutionProvider` only.
- No FAISS. The only vector backend is `sqlite-vec`.
- No network calls at import time. Model download happens on first use or via an explicit setup command.
- Only `amonhen.store` may contain SQL.
- Lower-layer modules (`decode`, `sample`, `encode`, `store`) never import each other or `pipeline`.
- No logic in `amonhen.cli` that cannot be called from Python.
- Human-facing messages go to stderr; data goes to stdout.
- Default database path is `~/.amonhen/index.db`. Default model cache is `~/.amonhen/models/`.
- Themed prose, banners, and colors are Stage 5. Stage 1 output is plain text only.
- OCR is Stage 6. Do not add OCR code, dependencies, or columns beyond the `ocr_text` column already in the schema.
- The adaptive sampler is Stage 2. Stage 1 ships the fixed sampler only.
- Every numeric claim about performance must come from measurement. Stage 1 makes no performance claims.

---

### Task 1: Project scaffold and tooling

**Files:**
- Create: `pyproject.toml`
- Create: `src/amonhen/__init__.py`
- Create: `.gitignore`
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: nothing.
- Produces: importable package `amonhen` exposing `__version__: str`. Test command `uv run pytest`. Lint command `uv run ruff check .`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_package.py`:

```python
import amonhen


def test_package_exposes_version():
    assert isinstance(amonhen.__version__, str)
    assert amonhen.__version__.count(".") >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen'`

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`:

```toml
[project]
name = "amonhen"
version = "0.1.0"
description = "Local, CPU-only video moment retrieval from the command line"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = [
    "numpy>=1.26",
    "onnxruntime>=1.18",
    "pillow>=10.0",
    "sqlite-vec>=0.1.6",
    "imageio-ffmpeg>=0.5",
    "typer>=0.12",
    "huggingface-hub>=0.24",
]

[project.scripts]
amon-hen = "amonhen.cli:app"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/amonhen"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: requires the real model or real video decoding",
]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Create `src/amonhen/__init__.py`:

```python
"""AmonHen: local, CPU-only video moment retrieval."""

__version__ = "0.1.0"
```

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.venv/
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
*.db
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_package.py -v`
Expected: PASS

Run: `uv run ruff check .`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/amonhen/__init__.py .gitignore tests/test_package.py
git commit -m "chore: scaffold amonhen package with uv, pytest, and ruff"
```

---

### Task 2: Confirm the model artifact and pin its identity

This task is a verification spike with a small permanent output. The spec flags model availability as the top risk: MobileCLIP2 ONNX exports exist publicly, but an INT8 variant is not confirmed. Everything downstream depends on the embedding dimension and the exact input/output names, so those get measured here and written down, never guessed.

**Files:**
- Create: `src/amonhen/model_registry.py`
- Test: `tests/test_model_registry.py`
- Modify: `docs/superpowers/specs/2026-08-19-amonhen-design.md` (section 14, record the finding)

**Interfaces:**
- Consumes: nothing.
- Produces: `ModelSpec` dataclass with fields `model_id: str`, `repo_id: str`, `vision_file: str`, `text_file: str`, `tokenizer_file: str`, `embed_dim: int`, `image_size: int`. Module-level `DEFAULT_MODEL: ModelSpec`, and `get_model(model_id: str) -> ModelSpec` raising `KeyError` for unknown ids.

- [ ] **Step 1: Download the candidate model and inspect it**

Run this throwaway probe script and read the output:

```bash
uv run python -c "
from huggingface_hub import snapshot_download
import onnxruntime as ort, pathlib
p = snapshot_download('plhery/mobileclip2-onnx')
for f in sorted(pathlib.Path(p).rglob('*.onnx')):
    print(f.relative_to(p), f.stat().st_size // 1024, 'KB')
"
```

Then, for the vision and text files that look right, print their signatures:

```bash
uv run python -c "
import onnxruntime as ort
s = ort.InferenceSession('PATH_TO_VISION.onnx', providers=['CPUExecutionProvider'])
print('IN ', [(i.name, i.shape, i.type) for i in s.get_inputs()])
print('OUT', [(o.name, o.shape, o.type) for o in s.get_outputs()])
"
```

Record: exact filenames, embedding dimension (last axis of the vision output), expected image size (spatial axes of the vision input), and whether an INT8 variant is present.

- [ ] **Step 2: Write the failing test using the measured values**

Create `tests/test_model_registry.py`. Replace the placeholder literals with the values measured in Step 1 before running it — this test is the record of what was measured:

```python
import pytest

from amonhen.model_registry import DEFAULT_MODEL, ModelSpec, get_model


def test_default_model_is_registered():
    assert get_model(DEFAULT_MODEL.model_id) is DEFAULT_MODEL


def test_default_model_fields_are_pinned():
    assert isinstance(DEFAULT_MODEL, ModelSpec)
    assert DEFAULT_MODEL.embed_dim == 512
    assert DEFAULT_MODEL.image_size == 256
    assert DEFAULT_MODEL.vision_file.endswith(".onnx")
    assert DEFAULT_MODEL.text_file.endswith(".onnx")


def test_unknown_model_raises():
    with pytest.raises(KeyError):
        get_model("no-such-model")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_model_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.model_registry'`

- [ ] **Step 4: Write minimal implementation**

Create `src/amonhen/model_registry.py`, substituting the measured values:

```python
"""Pinned identities of the ONNX models AmonHen can use.

The embedding dimension and image size are measured from the actual ONNX
files, never assumed: the store's vector column is declared from embed_dim,
and a mismatch corrupts an index silently rather than loudly.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    repo_id: str
    vision_file: str
    text_file: str
    tokenizer_file: str
    embed_dim: int
    image_size: int


MOBILECLIP2_S2 = ModelSpec(
    model_id="mobileclip2-s2",
    repo_id="plhery/mobileclip2-onnx",
    vision_file="MobileCLIP2-S2/vision_model.onnx",
    text_file="MobileCLIP2-S2/text_model.onnx",
    tokenizer_file="MobileCLIP2-S2/tokenizer.json",
    embed_dim=512,
    image_size=256,
)

DEFAULT_MODEL = MOBILECLIP2_S2

_REGISTRY = {spec.model_id: spec for spec in (MOBILECLIP2_S2,)}


def get_model(model_id: str) -> ModelSpec:
    return _REGISTRY[model_id]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_model_registry.py -v`
Expected: PASS

- [ ] **Step 6: Record the finding in the spec**

In section 14 of the spec, replace the unresolved model risk with what was actually measured: which repo and files are used, the embedding dimension, the image size, and whether INT8 was available. If INT8 was not available, state that Stage 1 ships FP32 and that quantisation moves to Stage 4 where its accuracy cost can be measured.

- [ ] **Step 7: Commit**

```bash
git add src/amonhen/model_registry.py tests/test_model_registry.py docs/superpowers/specs/2026-08-19-amonhen-design.md
git commit -m "feat: pin the MobileCLIP2 ONNX model identity

Measured the embedding dimension, image size, and file layout from the
real ONNX artifacts rather than assuming them, and recorded the finding
in the spec. The store declares its vector column from embed_dim, so a
wrong value here corrupts an index without any error."
```

---

### Task 3: Frame decoding

**Files:**
- Create: `src/amonhen/decode.py`
- Test: `tests/test_decode.py`
- Test: `tests/conftest.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Frame` dataclass with fields `ts_ms: int` and `image: numpy.ndarray` of shape `(H, W, 3)` and dtype `uint8` in RGB order. `iter_frames(path: str | Path, fps: float) -> Iterator[Frame]`. `probe(path: str | Path) -> VideoInfo` where `VideoInfo` has `duration_ms: int`, `fps: float`, `width: int`, `height: int`. `FFmpegError(RuntimeError)`.

- [ ] **Step 1: Write the shared video fixture**

Create `tests/conftest.py`:

```python
import subprocess

import imageio_ffmpeg
import pytest


@pytest.fixture(scope="session")
def ffmpeg_bin() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory, ffmpeg_bin) -> str:
    """A 4-second 32x32 test pattern at 10 fps: 40 frames, known duration."""
    path = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run(
        [
            ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=32x32:rate=10:duration=4",
            "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )
    return str(path)
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_decode.py`:

```python
import numpy as np
import pytest

from amonhen.decode import FFmpegError, iter_frames, probe


def test_probe_reads_duration_and_size(sample_video):
    info = probe(sample_video)
    assert 3800 <= info.duration_ms <= 4200
    assert info.width == 32
    assert info.height == 32
    assert 9.5 <= info.fps <= 10.5


def test_iter_frames_respects_target_fps(sample_video):
    frames = list(iter_frames(sample_video, fps=2.0))
    assert 7 <= len(frames) <= 9


def test_frames_carry_rgb_images_and_rising_timestamps(sample_video):
    frames = list(iter_frames(sample_video, fps=2.0))
    first = frames[0]
    assert first.image.shape == (32, 32, 3)
    assert first.image.dtype == np.uint8
    timestamps = [f.ts_ms for f in frames]
    assert timestamps == sorted(timestamps)
    assert timestamps[0] < timestamps[-1]


def test_missing_file_raises_ffmpeg_error(tmp_path):
    with pytest.raises(FFmpegError):
        probe(tmp_path / "nope.mp4")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_decode.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.decode'`

- [ ] **Step 4: Write minimal implementation**

Create `src/amonhen/decode.py`:

```python
"""Frame extraction via an ffmpeg subprocess.

Decoding dominates indexing time, so frame thinning is pushed into
ffmpeg's own filter graph: frames dropped by `-vf fps=` are never
decoded into Python at all. Reading every frame with a capture loop and
discarding most of them in Python would do the expensive work first and
throw the result away.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np


class FFmpegError(RuntimeError):
    pass


@dataclass(frozen=True)
class Frame:
    ts_ms: int
    image: np.ndarray


@dataclass(frozen=True)
class VideoInfo:
    duration_ms: int
    fps: float
    width: int
    height: int


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _ffprobe_json(path: Path) -> dict:
    # imageio-ffmpeg ships ffmpeg but not ffprobe, so the stream metadata is
    # read out of ffmpeg itself.
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    if "Invalid data" in proc.stderr or "No such file" in proc.stderr:
        raise FFmpegError(proc.stderr.strip().splitlines()[-1] if proc.stderr else "ffmpeg failed")
    return {"stderr": proc.stderr}


def probe(path: str | Path) -> VideoInfo:
    path = Path(path)
    if not path.exists():
        raise FFmpegError(f"file not found: {path}")

    stderr = _ffprobe_json(path)["stderr"]

    duration_ms = 0
    fps = 0.0
    width = height = 0
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            clock = line.split("Duration:")[1].split(",")[0].strip()
            hours, minutes, seconds = clock.split(":")
            duration_ms = int(
                (int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000
            )
        if "Video:" in line:
            for part in line.split(","):
                part = part.strip()
                if part.endswith("fps"):
                    fps = float(part[:-3].strip())
                if "x" in part and width == 0:
                    left, _, right = part.partition("x")
                    if left.strip().isdigit() and right.split()[0].isdigit():
                        width = int(left.strip())
                        height = int(right.split()[0])

    if width == 0 or height == 0:
        raise FFmpegError(f"no video stream found in {path}")

    return VideoInfo(duration_ms=duration_ms, fps=fps, width=width, height=height)


def iter_frames(path: str | Path, fps: float) -> Iterator[Frame]:
    path = Path(path)
    info = probe(path)
    frame_bytes = info.width * info.height * 3
    interval_ms = int(round(1000.0 / fps))

    command = [
        _ffmpeg(), "-hide_banner", "-loglevel", "error",
        "-i", str(path),
        "-vf", f"fps={fps}",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-",
    ]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None

    index = 0
    try:
        while True:
            buffer = proc.stdout.read(frame_bytes)
            if len(buffer) < frame_bytes:
                break
            image = np.frombuffer(buffer, dtype=np.uint8).reshape(
                info.height, info.width, 3
            )
            yield Frame(ts_ms=index * interval_ms, image=image)
            index += 1
    finally:
        proc.stdout.close()
        stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        code = proc.wait()
        if code != 0 and index == 0:
            raise FFmpegError(stderr.strip() or f"ffmpeg exited with {code}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_decode.py -v`
Expected: PASS

Run: `uv run ruff check .`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/amonhen/decode.py tests/test_decode.py tests/conftest.py
git commit -m "feat: add ffmpeg-backed frame decoding

Frames are thinned inside ffmpeg's filter graph rather than in Python,
so frames the sampler would discard are never decoded. Adds a synthetic
test-pattern fixture so the decode path is verified without shipping a
video file in the repository."
```

---

### Task 4: Embedding encoder

**Files:**
- Create: `src/amonhen/encode.py`
- Test: `tests/test_encode.py`

**Interfaces:**
- Consumes: `amonhen.model_registry.ModelSpec`, `DEFAULT_MODEL`, `get_model`.
- Produces: `ImageEncoder(spec: ModelSpec = DEFAULT_MODEL, session_factory=None)` with `embed(images: list[np.ndarray]) -> np.ndarray` of shape `(N, embed_dim)`, float32, L2-normalised rows. `TextEncoder(...)` with `embed(text: str) -> np.ndarray` of shape `(embed_dim,)`, float32, L2-normalised. `ensure_model(spec: ModelSpec) -> Path` downloading to `~/.amonhen/models/`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_encode.py`. The fake session lets the whole encoder be tested without downloading a model:

```python
import numpy as np
import pytest

from amonhen.encode import ImageEncoder, TextEncoder
from amonhen.model_registry import DEFAULT_MODEL


class FakeSession:
    """Stands in for onnxruntime.InferenceSession.

    Returns a deterministic non-normalised vector per input row so the
    test can assert that the encoder, not the model, does the
    normalisation.
    """

    def __init__(self, embed_dim: int, input_name: str = "input"):
        self.embed_dim = embed_dim
        self.input_name = input_name
        self.calls: list[np.ndarray] = []

    def get_inputs(self):
        class _In:
            name = self.input_name

        return [_In()]

    def get_outputs(self):
        class _Out:
            name = "output"

        return [_Out()]

    def run(self, _outputs, feed):
        batch = next(iter(feed.values()))
        self.calls.append(batch)
        n = batch.shape[0]
        out = np.tile(np.arange(self.embed_dim, dtype=np.float32), (n, 1))
        return [out * 3.0]


def test_image_encoder_returns_normalised_batch():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)
    images = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(3)]

    vectors = encoder.embed(images)

    assert vectors.shape == (3, DEFAULT_MODEL.embed_dim)
    assert vectors.dtype == np.float32
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_image_encoder_sends_one_batch_not_one_call_per_image():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    encoder.embed([np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(4)])

    assert len(fake.calls) == 1
    assert fake.calls[0].shape[0] == 4


def test_image_encoder_preprocesses_to_model_input_shape():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    encoder.embed([np.zeros((64, 48, 3), dtype=np.uint8)])

    batch = fake.calls[0]
    size = DEFAULT_MODEL.image_size
    assert batch.shape == (1, 3, size, size)
    assert batch.dtype == np.float32


def test_empty_batch_returns_empty_array_without_calling_the_model():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    vectors = encoder.embed([])

    assert vectors.shape == (0, DEFAULT_MODEL.embed_dim)
    assert fake.calls == []


def test_text_encoder_returns_single_normalised_vector():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = TextEncoder(
        DEFAULT_MODEL,
        session_factory=lambda spec: fake,
        tokenizer=lambda text: np.zeros((1, 77), dtype=np.int64),
    )

    vector = encoder.embed("a person in a yellow helmet")

    assert vector.shape == (DEFAULT_MODEL.embed_dim,)
    assert vector.dtype == np.float32
    assert np.isclose(np.linalg.norm(vector), 1.0, atol=1e-5)


@pytest.mark.slow
def test_real_model_produces_higher_similarity_for_matching_text():
    """Sanity check against the real model. Skipped by default."""
    image_encoder = ImageEncoder()
    text_encoder = TextEncoder()

    red = np.zeros((256, 256, 3), dtype=np.uint8)
    red[:, :, 0] = 220
    blue = np.zeros((256, 256, 3), dtype=np.uint8)
    blue[:, :, 2] = 220

    vectors = image_encoder.embed([red, blue])
    query = text_encoder.embed("a solid red image")

    assert float(vectors[0] @ query) > float(vectors[1] @ query)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_encode.py -v -m "not slow"`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.encode'`

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/encode.py`:

```python
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

# OpenCLIP normalisation constants; MobileCLIP2 inherits them.
_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)


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
```

If Task 2 found that the text model needs a different tokenizer or extra inputs such as an attention mask, adjust `_tokenize` and the feed dictionary to match what was measured, and add `tokenizers` to the dependency list in `pyproject.toml`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_encode.py -v -m "not slow"`
Expected: PASS

- [ ] **Step 5: Run the real-model check once**

Run: `uv run pytest tests/test_encode.py -v -m slow`
Expected: PASS. This downloads the model, so it is slow the first time. If it fails, the model wiring is wrong and no downstream task will work — fix it before continuing.

- [ ] **Step 6: Commit**

```bash
git add src/amonhen/encode.py tests/test_encode.py pyproject.toml
git commit -m "feat: add ONNX image and text encoders

Encoders take an injectable session factory so preprocessing, batching,
and normalisation are testable without downloading a model. Vectors are
L2-normalised at encode time, which makes cosine similarity a plain dot
product for every consumer. Batching is enforced because INT8 CPU
inference is heavily penalised at batch size one."
```

---

### Task 5: Storage layer

**Files:**
- Create: `src/amonhen/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `amonhen.model_registry.ModelSpec`.
- Produces: `Store(path: str | Path, embed_dim: int)` as a context manager, with:
  - `add_video(path: str, duration_ms: int, fps: float, size_bytes: int, mtime: float, sampler_config_hash: str, model_id: str) -> int` returning `video_id`
  - `add_frames(video_id: int, frames: list[FrameRecord]) -> None` where `FrameRecord` has `ts_ms: int`, `embedding: np.ndarray`, `kept_reason: str`
  - `search_vector(query: np.ndarray, limit: int) -> list[Hit]` where `Hit` has `video_id: int`, `video_path: str`, `ts_ms: int`, `score: float`
  - `list_videos() -> list[VideoRow]` where `VideoRow` has `id`, `path`, `duration_ms`, `frame_count`, `indexed_at`, `model_id`, `sampler_config_hash`
  - `needs_reindex(path, size_bytes, mtime, sampler_config_hash, model_id) -> bool`
  - `video_id_for_path(path: str) -> int | None`
  - `remove_video(video_id: int) -> None`
  - `stats() -> dict[str, int]` with keys `videos`, `frames`
  - `IncompatibleIndexError(RuntimeError)` raised when opening a database whose vector dimension differs from `embed_dim`

- [ ] **Step 1: Write the failing test**

Create `tests/test_store.py`:

```python
import numpy as np
import pytest

from amonhen.store import FrameRecord, IncompatibleIndexError, Store

DIM = 8


def unit(*values: float) -> np.ndarray:
    vector = np.array(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def basis(index: int) -> np.ndarray:
    vector = np.zeros(DIM, dtype=np.float32)
    vector[index] = 1.0
    return vector


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "index.db", embed_dim=DIM) as store:
        yield store


def add_sample_video(store, path="a.mp4", ts_list=(0, 1000, 2000)):
    video_id = store.add_video(
        path=path, duration_ms=3000, fps=25.0, size_bytes=123,
        mtime=1.0, sampler_config_hash="cfg1", model_id="m1",
    )
    store.add_frames(
        video_id,
        [
            FrameRecord(ts_ms=ts, embedding=basis(i), kept_reason="fixed")
            for i, ts in enumerate(ts_list)
        ],
    )
    return video_id


def test_add_video_and_frames_are_counted(store):
    add_sample_video(store)
    assert store.stats() == {"videos": 1, "frames": 3}


def test_search_returns_nearest_frame_first(store):
    add_sample_video(store)

    hits = store.search_vector(basis(1), limit=3)

    assert hits[0].ts_ms == 1000
    assert hits[0].video_path == "a.mp4"
    assert hits[0].score > hits[1].score


def test_search_spans_multiple_videos(store):
    add_sample_video(store, path="a.mp4")
    add_sample_video(store, path="b.mp4", ts_list=(5000, 6000, 7000))

    hits = store.search_vector(basis(0), limit=10)

    assert {hit.video_path for hit in hits} == {"a.mp4", "b.mp4"}


def test_scores_are_cosine_similarity_in_unit_range(store):
    add_sample_video(store)

    hits = store.search_vector(basis(0), limit=3)

    assert 0.99 <= hits[0].score <= 1.01
    assert all(-1.01 <= hit.score <= 1.01 for hit in hits)


def test_unchanged_video_does_not_need_reindex(store):
    add_sample_video(store)
    assert not store.needs_reindex("a.mp4", 123, 1.0, "cfg1", "m1")


def test_changed_mtime_needs_reindex(store):
    add_sample_video(store)
    assert store.needs_reindex("a.mp4", 123, 2.0, "cfg1", "m1")


def test_changed_sampler_config_needs_reindex(store):
    add_sample_video(store)
    assert store.needs_reindex("a.mp4", 123, 1.0, "cfg2", "m1")


def test_changed_model_needs_reindex(store):
    add_sample_video(store)
    assert store.needs_reindex("a.mp4", 123, 1.0, "cfg1", "m2")


def test_unknown_video_needs_reindex(store):
    assert store.needs_reindex("never-seen.mp4", 1, 1.0, "cfg1", "m1")


def test_remove_video_drops_its_frames(store):
    video_id = add_sample_video(store)

    store.remove_video(video_id)

    assert store.stats() == {"videos": 0, "frames": 0}
    assert store.search_vector(basis(0), limit=5) == []


def test_list_videos_reports_frame_counts(store):
    add_sample_video(store)

    rows = store.list_videos()

    assert len(rows) == 1
    assert rows[0].path == "a.mp4"
    assert rows[0].frame_count == 3


def test_opening_with_a_different_dimension_is_refused(tmp_path):
    path = tmp_path / "index.db"
    with Store(path, embed_dim=DIM) as store:
        add_sample_video(store)

    with pytest.raises(IncompatibleIndexError):
        Store(path, embed_dim=DIM + 1).__enter__()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.store'`

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/store.py`:

```python
"""SQLite persistence for video metadata, frames, and embeddings.

This is the only module in AmonHen that contains SQL.

The vector column's dimension is baked into the table at creation time,
so an index built with one model cannot be reopened with another. That
is enforced loudly here, because mixing embeddings from two models
produces plausible-looking nonsense rather than an error.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sqlite_vec

SCHEMA_VERSION = 1


class IncompatibleIndexError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrameRecord:
    ts_ms: int
    embedding: np.ndarray
    kept_reason: str


@dataclass(frozen=True)
class Hit:
    video_id: int
    video_path: str
    ts_ms: int
    score: float


@dataclass(frozen=True)
class VideoRow:
    id: int
    path: str
    duration_ms: int
    frame_count: int
    indexed_at: float
    model_id: str
    sampler_config_hash: str


class Store:
    def __init__(self, path: str | Path, embed_dim: int):
        self.path = Path(path)
        self.embed_dim = embed_dim
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        self._create_schema()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def _create_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS video (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                duration_ms INTEGER NOT NULL,
                fps REAL NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime REAL NOT NULL,
                indexed_at REAL NOT NULL,
                sampler_config_hash TEXT NOT NULL,
                model_id TEXT NOT NULL,
                score_baseline REAL
            );

            CREATE TABLE IF NOT EXISTS frame (
                id INTEGER PRIMARY KEY,
                video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
                ts_ms INTEGER NOT NULL,
                kept_reason TEXT NOT NULL,
                ocr_text TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_frame_video ON frame(video_id, ts_ms);
            """
        )

        stored_dim = cur.execute(
            "SELECT value FROM meta WHERE key = 'embed_dim'"
        ).fetchone()
        if stored_dim is None:
            cur.execute(
                "INSERT INTO meta(key, value) VALUES ('embed_dim', ?)",
                (str(self.embed_dim),),
            )
            cur.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        elif int(stored_dim["value"]) != self.embed_dim:
            self._conn.close()
            raise IncompatibleIndexError(
                f"index at {self.path} stores {stored_dim['value']}-dimensional "
                f"vectors, but {self.embed_dim} was requested. Re-index, or "
                f"use a different --db path."
            )

        cur.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_frame USING vec0(
                frame_id INTEGER PRIMARY KEY,
                embedding FLOAT[{self.embed_dim}]
            )
            """
        )
        self._conn.commit()

    def add_video(
        self,
        path: str,
        duration_ms: int,
        fps: float,
        size_bytes: int,
        mtime: float,
        sampler_config_hash: str,
        model_id: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO video(path, duration_ms, fps, size_bytes, mtime,
                              indexed_at, sampler_config_hash, model_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (path, duration_ms, fps, size_bytes, mtime, time.time(),
             sampler_config_hash, model_id),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def add_frames(self, video_id: int, frames: list[FrameRecord]) -> None:
        if not frames:
            return
        cur = self._conn.cursor()
        for record in frames:
            vector = np.asarray(record.embedding, dtype=np.float32)
            if vector.shape != (self.embed_dim,):
                raise ValueError(
                    f"expected a {self.embed_dim}-dimensional vector, got {vector.shape}"
                )
            cur.execute(
                "INSERT INTO frame(video_id, ts_ms, kept_reason) VALUES (?, ?, ?)",
                (video_id, record.ts_ms, record.kept_reason),
            )
            cur.execute(
                "INSERT INTO vec_frame(frame_id, embedding) VALUES (?, ?)",
                (cur.lastrowid, vector.tobytes()),
            )
        self._conn.commit()

    def search_vector(self, query: np.ndarray, limit: int) -> list[Hit]:
        vector = np.asarray(query, dtype=np.float32)
        rows = self._conn.execute(
            """
            SELECT v.frame_id AS frame_id, v.distance AS distance,
                   f.ts_ms AS ts_ms, f.video_id AS video_id, vid.path AS path
            FROM vec_frame v
            JOIN frame f ON f.id = v.frame_id
            JOIN video vid ON vid.id = f.video_id
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
            """,
            (vector.tobytes(), limit),
        ).fetchall()

        # sqlite-vec reports L2 distance. Both sides are unit vectors, so
        # cosine similarity is recovered exactly as 1 - d^2 / 2.
        return [
            Hit(
                video_id=row["video_id"],
                video_path=row["path"],
                ts_ms=row["ts_ms"],
                score=1.0 - (float(row["distance"]) ** 2) / 2.0,
            )
            for row in rows
        ]

    def needs_reindex(
        self,
        path: str,
        size_bytes: int,
        mtime: float,
        sampler_config_hash: str,
        model_id: str,
    ) -> bool:
        row = self._conn.execute(
            """
            SELECT size_bytes, mtime, sampler_config_hash, model_id
            FROM video WHERE path = ?
            """,
            (path,),
        ).fetchone()
        if row is None:
            return True
        return (
            row["size_bytes"] != size_bytes
            or abs(row["mtime"] - mtime) > 1e-6
            or row["sampler_config_hash"] != sampler_config_hash
            or row["model_id"] != model_id
        )

    def video_id_for_path(self, path: str) -> int | None:
        row = self._conn.execute(
            "SELECT id FROM video WHERE path = ?", (path,)
        ).fetchone()
        return int(row["id"]) if row else None

    def remove_video(self, video_id: int) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            DELETE FROM vec_frame
            WHERE frame_id IN (SELECT id FROM frame WHERE video_id = ?)
            """,
            (video_id,),
        )
        cur.execute("DELETE FROM frame WHERE video_id = ?", (video_id,))
        cur.execute("DELETE FROM video WHERE id = ?", (video_id,))
        self._conn.commit()

    def list_videos(self) -> list[VideoRow]:
        rows = self._conn.execute(
            """
            SELECT v.id, v.path, v.duration_ms, v.indexed_at, v.model_id,
                   v.sampler_config_hash, COUNT(f.id) AS frame_count
            FROM video v
            LEFT JOIN frame f ON f.video_id = v.id
            GROUP BY v.id
            ORDER BY v.indexed_at DESC
            """
        ).fetchall()
        return [
            VideoRow(
                id=row["id"],
                path=row["path"],
                duration_ms=row["duration_ms"],
                frame_count=row["frame_count"],
                indexed_at=row["indexed_at"],
                model_id=row["model_id"],
                sampler_config_hash=row["sampler_config_hash"],
            )
            for row in rows
        ]

    def stats(self) -> dict[str, int]:
        videos = self._conn.execute("SELECT COUNT(*) AS n FROM video").fetchone()["n"]
        frames = self._conn.execute("SELECT COUNT(*) AS n FROM frame").fetchone()["n"]
        return {"videos": int(videos), "frames": int(frames)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/store.py tests/test_store.py
git commit -m "feat: add sqlite-vec backed storage layer

Holds all SQL in one module and pins the vector dimension into the
database, refusing to reopen an index built with a different model.
Mixing embeddings from two models yields plausible-looking wrong results
rather than an error, so the check is made at open time. Records
kept_reason per frame so sampler efficiency can be audited later."
```

---

### Task 6: Fixed sampler

**Files:**
- Create: `src/amonhen/sample.py`
- Test: `tests/test_sample.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Sampler` protocol with `keep(frame) -> bool`, `reason: str`, and `config_hash() -> str`. `FixedSampler(fps: float)` implementing it, keeping every frame it is shown, with `reason == "fixed"`. `build_sampler(name: str, fps: float) -> Sampler` raising `ValueError` for unknown names.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sample.py`:

```python
import numpy as np
import pytest

from amonhen.sample import FixedSampler, build_sampler


def frame(value: int) -> np.ndarray:
    return np.full((16, 16, 3), value, dtype=np.uint8)


def test_fixed_sampler_keeps_every_frame():
    sampler = FixedSampler(fps=1.0)

    assert all(sampler.keep(frame(value)) for value in (0, 0, 255))


def test_fixed_sampler_reports_its_reason():
    assert FixedSampler(fps=1.0).reason == "fixed"


def test_config_hash_changes_with_fps():
    assert FixedSampler(fps=1.0).config_hash() != FixedSampler(fps=2.0).config_hash()


def test_config_hash_is_stable_for_equal_settings():
    assert FixedSampler(fps=1.0).config_hash() == FixedSampler(fps=1.0).config_hash()


def test_build_sampler_returns_fixed():
    assert isinstance(build_sampler("fixed", fps=1.0), FixedSampler)


def test_build_sampler_rejects_unknown_name():
    with pytest.raises(ValueError):
        build_sampler("adaptive", fps=1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sample.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.sample'`

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/sample.py`:

```python
"""Frame selection strategies.

Stage 1 ships only the fixed sampler, which keeps every frame ffmpeg
hands it. It exists as a real strategy rather than a special case
because Stage 4 benchmarks the adaptive sampler against it, and a
baseline that shares the interface is a baseline that can be measured
fairly.

config_hash() is stored alongside each indexed video. Changing sampler
settings changes the hash, which forces a re-index instead of silently
mixing frames selected under different rules.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np


class Sampler(Protocol):
    reason: str

    def keep(self, frame: np.ndarray) -> bool: ...

    def config_hash(self) -> str: ...


class FixedSampler:
    reason = "fixed"

    def __init__(self, fps: float):
        self.fps = fps

    def keep(self, frame: np.ndarray) -> bool:
        return True

    def config_hash(self) -> str:
        payload = f"fixed:fps={self.fps:.4f}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_sampler(name: str, fps: float) -> Sampler:
    if name == "fixed":
        return FixedSampler(fps=fps)
    raise ValueError(f"unknown sampler: {name!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sample.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/amonhen/sample.py tests/test_sample.py
git commit -m "feat: add the fixed frame sampler

Ships the benchmark baseline as a real strategy behind the sampler
interface rather than as a special case, so the adaptive sampler can be
measured against it on equal terms later. The config hash forces a
re-index when sampler settings change."
```

---

### Task 7: Pipeline

**Files:**
- Create: `src/amonhen/pipeline.py`
- Create: `src/amonhen/progress.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_progress.py`

**Interfaces:**
- Consumes: `decode.iter_frames`, `decode.probe`, `sample.build_sampler`, `encode.ImageEncoder`, `encode.TextEncoder`, `store.Store`, `store.FrameRecord`, `store.Hit`, `model_registry.DEFAULT_MODEL`.
- Produces:
  - `progress.Reporter` protocol with `video_started(path, total_ms)`, `frame_progress(decoded, kept, ts_ms)`, `video_finished(path, decoded, kept, elapsed_s)`, `run_finished(videos, frames, elapsed_s)`
  - `progress.NullReporter` and `progress.RecordingReporter` (the latter exposing `events: list[tuple]`)
  - `pipeline.IndexConfig` dataclass with `fps: float = 1.0`, `sampler: str = "fixed"`, `batch_size: int = 16`, `model_id: str = DEFAULT_MODEL.model_id`
  - `pipeline.IndexResult` dataclass with `videos: int`, `frames_decoded: int`, `frames_kept: int`, `skipped: list[str]`, `elapsed_s: float`
  - `pipeline.index_videos(paths, store, config, image_encoder, reporter=None, force=False) -> IndexResult`
  - `pipeline.search(query, store, text_encoder, limit=10) -> list[Hit]`
  - `pipeline.expand_paths(paths) -> list[Path]` resolving directories into video files

- [ ] **Step 1: Write the failing progress test**

Create `tests/test_progress.py`:

```python
from amonhen.progress import NullReporter, RecordingReporter


def test_null_reporter_accepts_every_event():
    reporter = NullReporter()
    reporter.video_started("a.mp4", 1000)
    reporter.frame_progress(1, 1, 0)
    reporter.video_finished("a.mp4", 1, 1, 0.5)
    reporter.run_finished(1, 1, 0.5)


def test_recording_reporter_captures_events_in_order():
    reporter = RecordingReporter()

    reporter.video_started("a.mp4", 1000)
    reporter.video_finished("a.mp4", 4, 3, 0.5)
    reporter.run_finished(1, 3, 0.5)

    names = [event[0] for event in reporter.events]
    assert names == ["video_started", "video_finished", "run_finished"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_progress.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.progress'`

- [ ] **Step 3: Implement the reporters**

Create `src/amonhen/progress.py`:

```python
"""Progress reporting seam between the pipeline and any user interface.

The pipeline calls a reporter and never imports a rendering library.
That keeps the whole indexing flow testable without a terminal, and
lets Stage 5 add a themed renderer without touching pipeline code.
"""

from __future__ import annotations

from typing import Protocol


class Reporter(Protocol):
    def video_started(self, path: str, total_ms: int) -> None: ...

    def frame_progress(self, decoded: int, kept: int, ts_ms: int) -> None: ...

    def video_finished(
        self, path: str, decoded: int, kept: int, elapsed_s: float
    ) -> None: ...

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None: ...


class NullReporter:
    def video_started(self, path: str, total_ms: int) -> None:
        pass

    def frame_progress(self, decoded: int, kept: int, ts_ms: int) -> None:
        pass

    def video_finished(self, path: str, decoded: int, kept: int, elapsed_s: float) -> None:
        pass

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        pass


class RecordingReporter:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def video_started(self, path: str, total_ms: int) -> None:
        self.events.append(("video_started", path, total_ms))

    def frame_progress(self, decoded: int, kept: int, ts_ms: int) -> None:
        self.events.append(("frame_progress", decoded, kept, ts_ms))

    def video_finished(self, path: str, decoded: int, kept: int, elapsed_s: float) -> None:
        self.events.append(("video_finished", path, decoded, kept, elapsed_s))

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        self.events.append(("run_finished", videos, frames, elapsed_s))
```

- [ ] **Step 4: Run it to verify it passes**

Run: `uv run pytest tests/test_progress.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing pipeline test**

Create `tests/test_pipeline.py`:

```python
import numpy as np
import pytest

from amonhen.pipeline import IndexConfig, expand_paths, index_videos, search
from amonhen.progress import RecordingReporter
from amonhen.store import Store

DIM = 8


class StubEncoder:
    """Maps a frame to a basis vector chosen by its mean pixel value.

    Deterministic and cheap, so the pipeline can be exercised end to end
    without ONNX or a real model.
    """

    def __init__(self, embed_dim: int = DIM):
        self.embed_dim = embed_dim
        self.batch_sizes: list[int] = []

    def embed(self, images):
        if not images:
            return np.zeros((0, self.embed_dim), dtype=np.float32)
        self.batch_sizes.append(len(images))
        out = np.zeros((len(images), self.embed_dim), dtype=np.float32)
        for row, image in enumerate(images):
            out[row, int(image.mean()) % self.embed_dim] = 1.0
        return out


class StubTextEncoder:
    def __init__(self, index: int, embed_dim: int = DIM):
        self.index = index
        self.embed_dim = embed_dim

    def embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.embed_dim, dtype=np.float32)
        vector[self.index] = 1.0
        return vector


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "index.db", embed_dim=DIM) as store:
        yield store


def test_index_writes_frames_for_a_real_video(store, sample_video):
    result = index_videos(
        [sample_video], store, IndexConfig(fps=2.0), StubEncoder()
    )

    assert result.videos == 1
    assert result.frames_kept > 0
    assert store.stats()["frames"] == result.frames_kept


def test_index_batches_frames_instead_of_encoding_one_at_a_time(store, sample_video):
    encoder = StubEncoder()

    index_videos([sample_video], store, IndexConfig(fps=2.0, batch_size=4), encoder)

    assert encoder.batch_sizes
    assert max(encoder.batch_sizes) <= 4
    assert max(encoder.batch_sizes) > 1


def test_reindexing_an_unchanged_video_is_skipped(store, sample_video):
    config = IndexConfig(fps=2.0)
    index_videos([sample_video], store, config, StubEncoder())

    second = index_videos([sample_video], store, config, StubEncoder())

    assert second.videos == 0
    assert second.skipped == [sample_video]


def test_force_reindexes_and_does_not_duplicate_frames(store, sample_video):
    config = IndexConfig(fps=2.0)
    first = index_videos([sample_video], store, config, StubEncoder())

    index_videos([sample_video], store, config, StubEncoder(), force=True)

    assert store.stats()["videos"] == 1
    assert store.stats()["frames"] == first.frames_kept


def test_changing_fps_forces_a_reindex(store, sample_video):
    index_videos([sample_video], store, IndexConfig(fps=2.0), StubEncoder())

    result = index_videos([sample_video], store, IndexConfig(fps=4.0), StubEncoder())

    assert result.videos == 1
    assert store.stats()["videos"] == 1


def test_reporter_receives_start_and_finish_events(store, sample_video):
    reporter = RecordingReporter()

    index_videos([sample_video], store, IndexConfig(fps=2.0), StubEncoder(), reporter)

    names = [event[0] for event in reporter.events]
    assert names[0] == "video_started"
    assert "video_finished" in names
    assert names[-1] == "run_finished"


def test_search_returns_hits_ordered_by_score(store, sample_video):
    index_videos([sample_video], store, IndexConfig(fps=2.0), StubEncoder())

    hits = search("anything", store, StubTextEncoder(index=0), limit=5)

    scores = [hit.score for hit in hits]
    assert scores == sorted(scores, reverse=True)
    assert all(hit.video_path == sample_video for hit in hits)


def test_expand_paths_finds_videos_in_a_directory(tmp_path, sample_video):
    import shutil

    shutil.copy(sample_video, tmp_path / "one.mp4")
    shutil.copy(sample_video, tmp_path / "two.mkv")
    (tmp_path / "notes.txt").write_text("ignore me")

    found = sorted(path.name for path in expand_paths([tmp_path]))

    assert found == ["one.mp4", "two.mkv"]
```

- [ ] **Step 6: Run it to verify it fails**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.pipeline'`

- [ ] **Step 7: Implement the pipeline**

Create `src/amonhen/pipeline.py`:

```python
"""The only module that knows the order of operations.

Everything below this layer is independent: decode does not know about
embeddings, encode does not know about video, store does not know where
its vectors came from. The cost of that isolation is paid here, once.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from amonhen import decode
from amonhen.model_registry import DEFAULT_MODEL
from amonhen.progress import NullReporter, Reporter
from amonhen.sample import build_sampler
from amonhen.store import FrameRecord, Hit, Store

VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpg", ".mpeg"}


@dataclass(frozen=True)
class IndexConfig:
    fps: float = 1.0
    sampler: str = "fixed"
    batch_size: int = 16
    model_id: str = DEFAULT_MODEL.model_id


@dataclass
class IndexResult:
    videos: int = 0
    frames_decoded: int = 0
    frames_kept: int = 0
    skipped: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0


def expand_paths(paths: Iterable[str | Path]) -> list[Path]:
    resolved: list[Path] = []
    for entry in paths:
        entry = Path(entry)
        if entry.is_dir():
            resolved.extend(
                sorted(
                    child
                    for child in entry.rglob("*")
                    if child.is_file() and child.suffix.lower() in VIDEO_SUFFIXES
                )
            )
        elif entry.is_file():
            resolved.append(entry)
    return resolved


def index_videos(
    paths: Iterable[str | Path],
    store: Store,
    config: IndexConfig,
    image_encoder,
    reporter: Reporter | None = None,
    force: bool = False,
) -> IndexResult:
    reporter = reporter or NullReporter()
    sampler = build_sampler(config.sampler, fps=config.fps)
    config_hash = sampler.config_hash()
    result = IndexResult()
    run_start = time.monotonic()

    for path in expand_paths(paths):
        key = str(path)
        stat = path.stat()

        if not force and not store.needs_reindex(
            key, stat.st_size, stat.st_mtime, config_hash, config.model_id
        ):
            result.skipped.append(key)
            continue

        existing = store.video_id_for_path(key)
        if existing is not None:
            store.remove_video(existing)

        info = decode.probe(path)
        reporter.video_started(key, info.duration_ms)
        video_start = time.monotonic()

        video_id = store.add_video(
            path=key,
            duration_ms=info.duration_ms,
            fps=info.fps,
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
            sampler_config_hash=config_hash,
            model_id=config.model_id,
        )

        decoded = kept = 0
        pending_images: list = []
        pending_ts: list[int] = []

        def flush() -> None:
            nonlocal pending_images, pending_ts
            if not pending_images:
                return
            vectors = image_encoder.embed(pending_images)
            store.add_frames(
                video_id,
                [
                    FrameRecord(ts_ms=ts, embedding=vectors[row], kept_reason=sampler.reason)
                    for row, ts in enumerate(pending_ts)
                ],
            )
            pending_images = []
            pending_ts = []

        for frame in decode.iter_frames(path, fps=config.fps):
            decoded += 1
            if not sampler.keep(frame.image):
                continue
            kept += 1
            pending_images.append(frame.image)
            pending_ts.append(frame.ts_ms)
            if len(pending_images) >= config.batch_size:
                flush()
            reporter.frame_progress(decoded, kept, frame.ts_ms)

        flush()

        elapsed = time.monotonic() - video_start
        reporter.video_finished(key, decoded, kept, elapsed)

        result.videos += 1
        result.frames_decoded += decoded
        result.frames_kept += kept

    result.elapsed_s = time.monotonic() - run_start
    reporter.run_finished(result.videos, result.frames_kept, result.elapsed_s)
    return result


def search(query: str, store: Store, text_encoder, limit: int = 10) -> list[Hit]:
    vector = text_encoder.embed(query)
    return store.search_vector(vector, limit=limit)
```

- [ ] **Step 8: Run it to verify it passes**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/amonhen/pipeline.py src/amonhen/progress.py tests/test_pipeline.py tests/test_progress.py
git commit -m "feat: add the indexing and search pipeline

Wires decode, sample, encode, and store together in the one module that
knows their order. Progress is delivered through a reporter interface so
the pipeline never imports a rendering library and the whole flow stays
testable without a terminal. Re-indexing is driven by file mtime, size,
sampler config, and model id, and a changed video replaces its old rows
rather than accumulating duplicates."
```

---

### Task 8: Command line interface

**Files:**
- Create: `src/amonhen/cli.py`
- Create: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 2 through 7.
- Produces: Typer application `app` with commands `index`, `search`, `videos`, `stats`, `setup`. Entry point `amon-hen`. Every command accepts `--db PATH` and `--json`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
import json

import numpy as np
import pytest
from typer.testing import CliRunner

from amonhen.cli import app

DIM = 8
runner = CliRunner()


class StubEncoder:
    embed_dim = DIM

    def embed(self, images):
        if not images:
            return np.zeros((0, DIM), dtype=np.float32)
        out = np.zeros((len(images), DIM), dtype=np.float32)
        for row, image in enumerate(images):
            out[row, int(image.mean()) % DIM] = 1.0
        return out


class StubTextEncoder:
    embed_dim = DIM

    def embed(self, text: str) -> np.ndarray:
        vector = np.zeros(DIM, dtype=np.float32)
        vector[0] = 1.0
        return vector


@pytest.fixture(autouse=True)
def stub_encoders(monkeypatch):
    """Replace the real encoders so CLI tests never download a model."""
    import amonhen.cli as cli

    monkeypatch.setattr(cli, "_build_image_encoder", lambda model_id: StubEncoder())
    monkeypatch.setattr(cli, "_build_text_encoder", lambda model_id: StubTextEncoder())
    monkeypatch.setattr(cli, "_embed_dim_for", lambda model_id: DIM)


def test_index_then_search_reports_a_hit(tmp_path, sample_video):
    db = tmp_path / "index.db"

    indexed = runner.invoke(app, ["index", sample_video, "--db", str(db)])
    assert indexed.exit_code == 0

    found = runner.invoke(app, ["search", "anything", "--db", str(db)])
    assert found.exit_code == 0
    assert "sample.mp4" in found.stdout


def test_search_json_output_is_parseable_and_undecorated(tmp_path, sample_video):
    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db), "--json"])

    result = runner.invoke(app, ["search", "anything", "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert isinstance(payload["results"], list)
    assert {"video", "ts_ms", "score"} <= set(payload["results"][0])
    assert "\x1b[" not in result.stdout


def test_index_json_output_reports_counts(tmp_path, sample_video):
    db = tmp_path / "index.db"

    result = runner.invoke(app, ["index", sample_video, "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert payload["videos"] == 1
    assert payload["frames_kept"] > 0


def test_videos_lists_what_was_indexed(tmp_path, sample_video):
    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    result = runner.invoke(app, ["videos", "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert len(payload["videos"]) == 1
    assert payload["videos"][0]["frame_count"] > 0


def test_stats_reports_totals(tmp_path, sample_video):
    db = tmp_path / "index.db"
    runner.invoke(app, ["index", sample_video, "--db", str(db)])

    result = runner.invoke(app, ["stats", "--db", str(db), "--json"])

    payload = json.loads(result.stdout)
    assert payload["videos"] == 1
    assert payload["frames"] > 0


def test_search_on_an_empty_index_exits_cleanly(tmp_path):
    db = tmp_path / "empty.db"

    result = runner.invoke(app, ["search", "anything", "--db", str(db), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["results"] == []


def test_missing_video_file_fails_with_a_clear_message(tmp_path):
    result = runner.invoke(
        app, ["index", str(tmp_path / "nope.mp4"), "--db", str(tmp_path / "i.db")]
    )

    assert result.exit_code != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'amonhen.cli'`

- [ ] **Step 3: Write minimal implementation**

Create `src/amonhen/cli.py`:

```python
"""Command line surface.

Deliberately thin: every command is a call into `pipeline` plus output
formatting. Anything a command can do must also be reachable from
Python, so nothing worth testing lives here.

Stage 1 prints plain text. The interactive session, the banner, and the
theme arrive in Stage 5 and replace only the rendering, not the flow.

Data goes to stdout and human-facing messages go to stderr, so the
output can be piped.
"""

from __future__ import annotations

import json as jsonlib
import sys
from pathlib import Path

import typer

from amonhen import __version__
from amonhen.model_registry import DEFAULT_MODEL, get_model
from amonhen.pipeline import IndexConfig, index_videos, search as run_search
from amonhen.progress import NullReporter
from amonhen.store import IncompatibleIndexError, Store

app = typer.Typer(
    add_completion=False,
    help="Search your videos by describing what you are looking for. Runs locally on CPU.",
)

DEFAULT_DB = Path.home() / ".amonhen" / "index.db"


def _build_image_encoder(model_id: str):
    from amonhen.encode import ImageEncoder

    return ImageEncoder(get_model(model_id))


def _build_text_encoder(model_id: str):
    from amonhen.encode import TextEncoder

    return TextEncoder(get_model(model_id))


def _embed_dim_for(model_id: str) -> int:
    return get_model(model_id).embed_dim


def _open_store(db: Path, model_id: str) -> Store:
    try:
        return Store(db, embed_dim=_embed_dim_for(model_id))
    except IncompatibleIndexError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error


def _format_timestamp(ts_ms: int) -> str:
    total_seconds, milliseconds = divmod(int(ts_ms), 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds // 100}"


@app.command()
def index(
    paths: list[str] = typer.Argument(..., help="Video files or directories to index."),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    fps: float = typer.Option(1.0, "--fps", help="Frames sampled per second of video."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    force: bool = typer.Option(False, "--force", help="Re-index even if unchanged."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """Index one or more videos into the local database."""
    for path in paths:
        if not Path(path).exists():
            typer.echo(f"not found: {path}", err=True)
            raise typer.Exit(code=1)

    store = _open_store(db, model)
    try:
        result = index_videos(
            paths,
            store,
            IndexConfig(fps=fps, model_id=model),
            _build_image_encoder(model),
            NullReporter(),
            force=force,
        )
    finally:
        store.close()

    if json:
        typer.echo(
            jsonlib.dumps(
                {
                    "videos": result.videos,
                    "frames_decoded": result.frames_decoded,
                    "frames_kept": result.frames_kept,
                    "skipped": result.skipped,
                    "elapsed_s": round(result.elapsed_s, 3),
                }
            )
        )
        return

    typer.echo(
        f"Indexed {result.videos} video(s), {result.frames_kept} frames "
        f"in {result.elapsed_s:.1f}s"
    )
    for skipped in result.skipped:
        typer.echo(f"unchanged, skipped: {skipped}", err=True)


@app.command()
def search(
    query: str = typer.Argument(..., help="What to look for."),
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    limit: int = typer.Option(10, "--limit", "-k", help="Maximum results."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """Find moments matching a text description."""
    store = _open_store(db, model)
    try:
        hits = run_search(query, store, _build_text_encoder(model), limit=limit)
    finally:
        store.close()

    if json:
        typer.echo(
            jsonlib.dumps(
                {
                    "query": query,
                    "results": [
                        {
                            "video": hit.video_path,
                            "ts_ms": hit.ts_ms,
                            "score": round(hit.score, 4),
                        }
                        for hit in hits
                    ],
                }
            )
        )
        return

    if not hits:
        typer.echo("No results.", err=True)
        return

    for position, hit in enumerate(hits, start=1):
        name = Path(hit.video_path).name
        typer.echo(
            f"{position:>2}. {_format_timestamp(hit.ts_ms)}  {hit.score:.3f}  {name}"
        )


@app.command()
def videos(
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """List indexed videos."""
    store = _open_store(db, model)
    try:
        rows = store.list_videos()
    finally:
        store.close()

    if json:
        typer.echo(
            jsonlib.dumps(
                {
                    "videos": [
                        {
                            "path": row.path,
                            "duration_ms": row.duration_ms,
                            "frame_count": row.frame_count,
                            "model_id": row.model_id,
                        }
                        for row in rows
                    ]
                }
            )
        )
        return

    for row in rows:
        typer.echo(
            f"{_format_timestamp(row.duration_ms)}  {row.frame_count:>6} frames  {row.path}"
        )


@app.command()
def stats(
    db: Path = typer.Option(DEFAULT_DB, "--db", help="Index database path."),
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> None:
    """Show index totals."""
    store = _open_store(db, model)
    try:
        totals = store.stats()
    finally:
        store.close()

    if json:
        typer.echo(jsonlib.dumps(totals))
        return

    typer.echo(f"videos: {totals['videos']}")
    typer.echo(f"frames: {totals['frames']}")


@app.command()
def setup(
    model: str = typer.Option(DEFAULT_MODEL.model_id, "--model", help="Model id."),
) -> None:
    """Download the model files ahead of first use."""
    from amonhen.encode import ensure_model

    spec = get_model(model)
    typer.echo(f"Downloading {spec.repo_id} ...", err=True)
    location = ensure_model(spec)
    typer.echo(f"Model ready at {location}", err=True)


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


def main() -> None:
    sys.exit(app())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Run the whole suite and the linter**

Run: `uv run pytest -v -m "not slow"`
Expected: PASS, all tests.

Run: `uv run ruff check .`
Expected: no errors.

- [ ] **Step 6: Verify the real end-to-end flow by hand**

Point it at an actual video file, not the synthetic fixture:

```bash
uv run amon-hen index /path/to/a/real/video.mp4 --db ./scratch.db --fps 1
uv run amon-hen search "a person" --db ./scratch.db
uv run amon-hen stats --db ./scratch.db
```

Expected: indexing reports a frame count, search returns timestamps ordered by score, and the top results are plausibly related to the query. If they are not, the model wiring from Task 4 is wrong — a passing test suite does not prove the embeddings are meaningful, only that they flow through the system.

- [ ] **Step 7: Write the README**

Create `README.md`. Describe what AmonHen is, the installation command, the two commands above with their real output, and — explicitly — the limitations: it finds objects and scenes rather than actions, it is tested on Windows and Linux x86, and it makes no accuracy or speed claims yet because Stage 4 has not measured them. Do not mention Raspberry Pi, Jetson, or edge devices. Do not quote Tolkien's books or films.

- [ ] **Step 8: Commit**

```bash
git add src/amonhen/cli.py tests/test_cli.py README.md
git commit -m "feat: add the index, search, videos, stats, and setup commands

Every command is a call into the pipeline plus formatting, so nothing
that matters lives in the CLI layer. Each command supports --json with
data on stdout and human-facing messages on stderr, which keeps the
output pipeable and gives Stage 5 a themed renderer to replace without
touching the flow."
```

---

## Stage 1 done when

- `uv run pytest -m "not slow"` passes.
- `uv run ruff check .` is clean.
- `amon-hen index` on a real video writes frames, and `amon-hen search` returns timestamps that plausibly match the query.
- Re-running `index` on an unchanged file skips it; changing `--fps` re-indexes it.
- `--json` output parses and contains no escape codes.
- README states the limitations and contains no unmeasured numbers.

## What Stage 1 deliberately does not do

The adaptive sampler is Stage 2, segment merging and score calibration are Stage 3, the benchmark harness is Stage 4, the interactive themed interface is Stage 5, OCR is Stage 6, and packaging and release are Stage 7.

Stage 1 search returns individual frame timestamps rather than merged segments, and returns the top `k` regardless of how weak the match is. Both are known gaps, filled in Stage 3.
