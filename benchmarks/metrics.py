"""Evaluation metrics for Video Moment Retrieval and CPU indexing efficiency."""

from __future__ import annotations

from dataclasses import dataclass

from amonhen.segment import Segment


def compute_iou(
    pred_start_s: float,
    pred_end_s: float,
    gt_start_s: float,
    gt_end_s: float,
) -> float:
    """Calculate Intersection-over-Union (IoU) between two temporal windows in seconds."""
    intersection_start = max(pred_start_s, gt_start_s)
    intersection_end = min(pred_end_s, gt_end_s)
    intersection = max(0.0, intersection_end - intersection_start)

    union_start = min(pred_start_s, gt_start_s)
    union_end = max(pred_end_s, gt_end_s)
    union = max(0.0, union_end - union_start)

    if union <= 0.0:
        return 0.0
    return float(intersection / union)


@dataclass(frozen=True)
class QueryResult:
    best_iou: float
    r1_03: bool
    r1_05: bool
    r5_03: bool
    r5_05: bool
    latency_ms: float


def evaluate_query(
    segments: list[Segment],
    gt_start_s: float,
    gt_end_s: float,
    latency_ms: float = 0.0,
) -> QueryResult:
    """Evaluate predicted segments against ground truth temporal window."""
    if not segments:
        return QueryResult(
            best_iou=0.0,
            r1_03=False,
            r1_05=False,
            r5_03=False,
            r5_05=False,
            latency_ms=latency_ms,
        )

    # Top-1 segment
    top1 = segments[0]
    iou_top1 = compute_iou(
        top1.start_ms / 1000.0,
        top1.end_ms / 1000.0,
        gt_start_s,
        gt_end_s,
    )

    # Top-5 max IoU
    ious_top5 = [
        compute_iou(
            s.start_ms / 1000.0,
            s.end_ms / 1000.0,
            gt_start_s,
            gt_end_s,
        )
        for s in segments[:5]
    ]
    max_iou_top5 = max(ious_top5)

    return QueryResult(
        best_iou=iou_top1,
        r1_03=iou_top1 >= 0.3,
        r1_05=iou_top1 >= 0.5,
        r5_03=max_iou_top5 >= 0.3,
        r5_05=max_iou_top5 >= 0.5,
        latency_ms=latency_ms,
    )


@dataclass(frozen=True)
class BenchmarkReport:
    config_name: str
    r1_03: float
    r1_05: float
    r5_03: float
    miou: float
    indexing_speedup: float
    avg_latency_ms: float
    storage_mb_per_hour: float
    frames_kept_pct: float


def format_markdown_table(reports: list[BenchmarkReport]) -> str:
    """Format benchmark reports into a Markdown comparison table."""
    lines = [
        (
            "| Sampler Configuration | R@1 (IoU=0.3) | R@1 (IoU=0.5) | R@5 (IoU=0.3) | mIoU "
            "| Indexing Speed | Latency | Storage / Hour |"
        ),
        "|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for r in reports:
        lines.append(
            f"| **{r.config_name}** | {r.r1_03:.3f} | {r.r1_05:.3f} | {r.r5_03:.3f} | "
            f"{r.miou:.3f} | {r.indexing_speedup:.1f}x RT | {r.avg_latency_ms:.1f} ms | "
            f"{r.storage_mb_per_hour:.1f} MB |"
        )
    return "\n".join(lines)
