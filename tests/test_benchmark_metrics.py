from benchmarks.metrics import (
    BenchmarkReport,
    compute_iou,
    evaluate_query,
    format_markdown_table,
)

from amonhen.segment import Segment


def test_compute_iou_exact_match():
    assert compute_iou(10.0, 20.0, 10.0, 20.0) == 1.0


def test_compute_iou_disjoint():
    assert compute_iou(0.0, 5.0, 10.0, 15.0) == 0.0


def test_compute_iou_partial_overlap():
    # Intersection = [10, 15] (5s), Union = [5, 20] (15s) -> 5/15 = 1/3
    assert abs(compute_iou(5.0, 15.0, 10.0, 20.0) - (1.0 / 3.0)) < 1e-5


def test_evaluate_query_computes_recall_and_miou():
    seg1 = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=10000,
        end_ms=20000,
        best_ts_ms=15000,
        score=0.9,
        frame_count=5,
    )
    seg2 = Segment(
        video_id=1,
        video_path="v.mp4",
        start_ms=30000,
        end_ms=40000,
        best_ts_ms=35000,
        score=0.8,
        frame_count=5,
    )

    # GT is 12s to 18s (inside seg1)
    res = evaluate_query(
        [seg1, seg2], gt_start_s=12.0, gt_end_s=18.0, latency_ms=15.0
    )

    assert res.r1_03 is True
    assert res.r1_05 is True
    assert res.best_iou > 0.5
    assert res.latency_ms == 15.0


def test_format_markdown_table():
    reports = [
        BenchmarkReport(
            config_name="Fixed (1.0 fps)",
            r1_03=0.45,
            r1_05=0.30,
            r5_03=0.75,
            miou=0.35,
            indexing_speedup=8.5,
            avg_latency_ms=18.2,
            storage_mb_per_hour=12.4,
            frames_kept_pct=100.0,
        )
    ]
    table = format_markdown_table(reports)
    assert "Fixed (1.0 fps)" in table
    assert "8.5x RT" in table
    assert "18.2 ms" in table
