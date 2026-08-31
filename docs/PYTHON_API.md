# Amon Hen Python API Guide

Amon Hen can be embedded directly as a Python library into computer vision pipelines, video editing tools, and search services.

---

## 1. Installation

```bash
pip install amon-hen
```

---

## 2. Basic Search Example

```python
from pathlib import Path
from amonhen.encode import TextEncoder
from amonhen.model_registry import get_model
from amonhen.pipeline import search
from amonhen.store import Store

# 1. Connect to SQLite vector store
store = Store(Path("index.db"))

# 2. Load CPU-optimized ONNX Text Encoder (downloads model automatically if needed)
spec = get_model("mobileclip2-s0")
text_encoder = TextEncoder(spec)

# 3. Search moments
query = "a red sports car turning at intersection"
results = search(
    query=query,
    store=store,
    text_encoder=text_encoder,
    limit=5,
    max_gap_ms=4000,  # Merge candidate frames within 4.0s gap
    calibrate=True,  # Use statistical noise baseline calibration
)

# 4. Process retrieved segments
for i, seg in enumerate(results, start=1):
    print(f"#{i} Video: {seg.video_path}")
    print(f"   Time Range: {seg.start_ms / 1000.0:.1f}s - {seg.end_ms / 1000.0:.1f}s")
    print(f"   Peak Moment: {seg.best_ts_ms / 1000.0:.1f}s")
    print(f"   Score: {seg.score:.4f} (from {seg.frame_count} frames)\n")

store.close()
```

---

## 3. Programmatic Video Indexing

```python
from pathlib import Path
from amonhen.encode import ImageEncoder, TextEncoder
from amonhen.model_registry import get_model
from amonhen.pipeline import IndexConfig, index_videos
from amonhen.progress import NullReporter
from amonhen.store import Store

store = Store(Path("index.db"))
spec = get_model("mobileclip2-s0")

image_encoder = ImageEncoder(spec)
text_encoder = TextEncoder(spec)

# Configure 3-gate adaptive sampler
config = IndexConfig(
    fps=1.0,
    sampler="adaptive",
    embed_dedup_threshold=0.98,
    dedup_hamming_threshold=4,
    blur_sharpness_threshold=None,
)

# Index videos (accepts files or directories)
result = index_videos(
    paths=[Path("video1.mp4"), Path("video2.mp4")],
    store=store,
    config=config,
    image_encoder=image_encoder,
    reporter=NullReporter(),
    text_encoder=text_encoder,
)

print(
    f"Indexed {result.videos} video(s), "
    f"kept {result.frames_kept}/{result.frames_decoded} frames in {result.elapsed_s:.2f}s"
)
store.close()
```

---

## 4. Extracting Video Clips Programmatically

```python
from pathlib import Path
from amonhen.cutter import cut_video_segment

# Lossless stream-copy extraction (< 0.2s, no re-encoding)
clip_path = cut_video_segment(
    video_path=Path("footage.mp4"),
    start_ms=37_000,
    end_ms=66_000,
    out_path=Path("highlight.mp4"),
    reencode=False,
)
print(f"Exported clip to: {clip_path}")

# Frame-accurate re-encoded cut
clip_reencoded = cut_video_segment(
    video_path=Path("footage.mp4"),
    start_ms=10_500,
    end_ms=25_200,
    reencode=True,
)
print(f"Exported frame-accurate clip to: {clip_reencoded}")
```

---

## 5. Standalone Vision & Text Embedding Generation

```python
import numpy as np
from PIL import Image
from amonhen.encode import ImageEncoder, TextEncoder
from amonhen.model_registry import get_model

spec = get_model("mobileclip2-s0")
vis_encoder = ImageEncoder(spec)
txt_encoder = TextEncoder(spec)

# Embed image (PIL Image -> 512-dim L2-normalized numpy array)
img = Image.open("sample.jpg").convert("RGB")
img_vec = vis_encoder.encode_image(img)

# Embed text (string -> 512-dim L2-normalized numpy array)
txt_vec = txt_encoder.encode_text("a golden retriever playing in grass")

# Compute cosine similarity
similarity = float(np.dot(img_vec, txt_vec))
print(f"Cosine Similarity: {similarity:.4f}")
```

