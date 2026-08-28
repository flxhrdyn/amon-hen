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

    def video_finished(self, path: str, decoded: int, stored: int, elapsed_s: float) -> None: ...

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


class RichReporter:
    """Rich dual-level terminal progress reporter conforming to Reporter protocol."""

    def __init__(self, plain: bool = False) -> None:
        from pathlib import Path

        self._path_cls = Path
        self.plain = plain
        self._current_video: str = ""
        self._total_ms: int = 0
        self._progress = None
        self._video_task = None

        if not self.plain:
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TaskProgressColumn,
                TextColumn,
                TimeElapsedColumn,
                TimeRemainingColumn,
            )

            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold yellow]{task.description}[/bold yellow]"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                TimeElapsedColumn(),
                transient=True,
            )

    def video_started(self, path: str, total_ms: int) -> None:
        self._current_video = self._path_cls(path).name
        self._total_ms = total_ms
        if self._progress is not None:
            if not self._progress.live.is_started:
                self._progress.start()
            self._video_task = self._progress.add_task(
                self._current_video,
                total=total_ms,
            )

    def frame_progress(self, decoded: int, stored: int, ts_ms: int) -> None:
        if self._progress is not None and self._video_task is not None:
            desc = f"{self._current_video} ({stored}/{decoded} kept)"
            self._progress.update(
                self._video_task,
                completed=min(ts_ms, self._total_ms) if self._total_ms > 0 else ts_ms,
                description=desc,
            )

    def video_finished(self, path: str, decoded: int, stored: int, elapsed_s: float) -> None:
        if self._progress is not None and self._video_task is not None:
            self._progress.update(
                self._video_task,
                completed=self._total_ms,
            )
            self._progress.remove_task(self._video_task)
            self._video_task = None

    def run_finished(self, videos: int, frames: int, elapsed_s: float) -> None:
        if self._progress is not None and self._progress.live.is_started:
            self._progress.stop()

    def __del__(self) -> None:
        if getattr(self, "_progress", None) is not None and self._progress.live.is_started:
            self._progress.stop()
