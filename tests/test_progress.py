from amonhen.progress import NullReporter, RecordingReporter, RichReporter


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


def test_rich_reporter_handles_full_lifecycle():
    reporter = RichReporter(plain=True)
    reporter.video_started("test.mp4", total_ms=10000)
    reporter.frame_progress(decoded=10, stored=5, ts_ms=5000)
    reporter.video_finished("test.mp4", decoded=20, stored=10, elapsed_s=1.5)
    reporter.run_finished(videos=1, frames=10, elapsed_s=1.5)


def test_rich_reporter_handles_full_lifecycle_plain_false():
    reporter = RichReporter(plain=False)
    reporter.video_started("test.mp4", total_ms=10000)
    reporter.frame_progress(decoded=10, stored=5, ts_ms=5000)
    reporter.video_finished("test.mp4", decoded=20, stored=10, elapsed_s=1.5)
    reporter.run_finished(videos=1, frames=10, elapsed_s=1.5)


def test_rich_reporter_multiple_videos():
    reporter = RichReporter(plain=False)
    reporter.video_started("v1.mp4", total_ms=5000)
    reporter.frame_progress(decoded=5, stored=2, ts_ms=2500)
    reporter.video_finished("v1.mp4", decoded=10, stored=4, elapsed_s=1.0)

    reporter.video_started("v2.mp4", total_ms=0)
    reporter.frame_progress(decoded=3, stored=1, ts_ms=1000)
    reporter.video_finished("v2.mp4", decoded=6, stored=2, elapsed_s=0.5)

    reporter.run_finished(videos=2, frames=6, elapsed_s=1.5)


