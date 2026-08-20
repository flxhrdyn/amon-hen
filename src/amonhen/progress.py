"""Progress reporting seam between the pipeline and any user interface.

The pipeline calls a reporter and never imports a rendering library.
That keeps the whole indexing flow testable without a terminal, and
lets Stage 5 add a themed renderer without touching pipeline code.

`decoded` counts frames ffmpeg handed over; `stored` counts frames that
survived every gate and reached the index. Both callbacks report the
same `stored` figure, so a progress line never contradicts the total
printed when the video finishes.
"""

from __future__ import annotations

from typing import Protocol


class Reporter(Protocol):
    def video_started(self, path: str, total_ms: int) -> None: ...

    def frame_progress(self, decoded: int, stored: int, ts_ms: int) -> None: ...

    def video_finished(
        self, path: str, decoded: int, stored: int, elapsed_s: float
    ) -> None: ...

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None: ...


class NullReporter:
    def video_started(self, path: str, total_ms: int) -> None:
        pass

    def frame_progress(self, decoded: int, stored: int, ts_ms: int) -> None:
        pass

    def video_finished(self, path: str, decoded: int, stored: int, elapsed_s: float) -> None:
        pass

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        pass


class RecordingReporter:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def video_started(self, path: str, total_ms: int) -> None:
        self.events.append(("video_started", path, total_ms))

    def frame_progress(self, decoded: int, stored: int, ts_ms: int) -> None:
        self.events.append(("frame_progress", decoded, stored, ts_ms))

    def video_finished(self, path: str, decoded: int, stored: int, elapsed_s: float) -> None:
        self.events.append(("video_finished", path, decoded, stored, elapsed_s))

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        self.events.append(("run_finished", videos, frames, elapsed_s))
