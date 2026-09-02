from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from amonhen.pipeline import search
from amonhen.store import SpeechSegment, Store


def test_search_hybrid_combines_visual_and_speech(tmp_path: Path):
    db_path = tmp_path / "test_hybrid.db"
    store = Store(db_path, embed_dim=4)

    v1_id = store.add_video(
        path="/videos/sample1.mp4",
        duration_ms=30000,
        fps=30.0,
        size_bytes=1024,
        mtime=1.0,
        sampler_config_hash="abc",
        model_id="mobileclip2-s0",
    )
    store.mark_complete(v1_id)

    # Add speech segment to video 1
    store.add_speech_segments(
        v1_id,
        [
            SpeechSegment(start_ms=5000, end_ms=8000, text="There is a red umbrella on the table"),
        ],
    )

    mock_text_encoder = MagicMock()
    mock_text_encoder.embed.return_value = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    # Perform hybrid search for "umbrella"
    results = search("umbrella", store=store, text_encoder=mock_text_encoder, mode="hybrid")

    assert len(results) >= 1
    speech_result = next((r for r in results if r.match_type in ("speech", "hybrid")), None)
    assert speech_result is not None
    assert speech_result.spoken_text == "There is a red umbrella on the table"
    assert speech_result.start_ms == 5000
    assert speech_result.end_ms == 8000

    store.close()
