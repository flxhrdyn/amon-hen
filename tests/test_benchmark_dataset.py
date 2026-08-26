import json

from benchmarks.dataset import generate_synthetic_benchmark, load_dataset


def test_load_dataset_parses_json(tmp_path):
    video_file = tmp_path / "vid.mp4"
    video_file.write_bytes(b"dummy")
    annotation_data = [
        {
            "video_path": str(video_file),
            "duration_s": 20.0,
            "annotations": [
                {"query": "person jumping", "start_s": 5.0, "end_s": 10.0}
            ],
        }
    ]
    json_path = tmp_path / "annotations.json"
    json_path.write_text(json.dumps(annotation_data), encoding="utf-8")

    dataset = load_dataset(json_path)
    assert len(dataset) == 1
    assert dataset[0].duration_s == 20.0
    assert len(dataset[0].annotations) == 1
    assert dataset[0].annotations[0].query == "person jumping"


def test_generate_synthetic_benchmark_creates_videos(tmp_path):
    dataset = generate_synthetic_benchmark(tmp_path / "synthetic", count=1)
    assert len(dataset) == 1
    assert dataset[0].video_path.exists()
    assert dataset[0].duration_s > 0
    assert len(dataset[0].annotations) >= 1
