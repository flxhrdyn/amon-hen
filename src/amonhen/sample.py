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


def _grayscale(frame: np.ndarray) -> np.ndarray:
    return frame.astype(np.float32).mean(axis=2)


def _sharpness(gray: np.ndarray) -> float:
    return float(np.diff(gray, axis=0).var() + np.diff(gray, axis=1).var())


def _phash(gray: np.ndarray, size: int = 8) -> np.ndarray:
    rows = np.array_split(gray, size, axis=0)
    small = np.array([[cell.mean() for cell in np.array_split(row, size, axis=1)] for row in rows])
    return small > small.mean()


class AdaptiveSampler:
    """Two-gate frame filter: drops near-duplicates and blurry frames.

    The third gate (embedding-similarity dedup) lives in the pipeline,
    since it needs the encoded vector these two gates never see.
    """

    reason = "adaptive"

    def __init__(
        self,
        fps: float,
        dedup_hamming_threshold: int = 4,
        blur_sharpness_threshold: float = 10.0,
    ):
        self.fps = fps
        self.dedup_hamming_threshold = dedup_hamming_threshold
        self.blur_sharpness_threshold = blur_sharpness_threshold
        self._last_hash: np.ndarray | None = None

    def keep(self, frame: np.ndarray) -> bool:
        gray = _grayscale(frame)

        if _sharpness(gray) < self.blur_sharpness_threshold:
            return False

        current_hash = _phash(gray)
        if self._last_hash is not None:
            distance = int(np.count_nonzero(current_hash != self._last_hash))
            if distance <= self.dedup_hamming_threshold:
                return False

        self._last_hash = current_hash
        return True

    def config_hash(self) -> str:
        payload = (
            f"adaptive:fps={self.fps:.4f}"
            f":dedup={self.dedup_hamming_threshold}"
            f":blur={self.blur_sharpness_threshold:.4f}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_sampler(name: str, fps: float) -> Sampler:
    if name == "fixed":
        return FixedSampler(fps=fps)
    if name == "adaptive":
        return AdaptiveSampler(fps=fps)
    raise ValueError(f"unknown sampler: {name!r}")
