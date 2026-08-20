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
