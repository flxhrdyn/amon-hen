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
