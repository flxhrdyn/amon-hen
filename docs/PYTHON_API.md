# Amon Hen Python API Guide

Amon Hen can be embedded directly as a Python library into computer vision pipelines, video editing tools, and search services.

---

## 1. Installation

```bash
pip install amonhen
```

---

## 2. Basic Search Example

```python
from pathlib import Path
from amonhen.model_registry import get_model
from amonhen.encode import TextEncoder
from amonhen.store import Store
from amonhen.pipeline import search

# 1. Connect to SQLite vector store
store = Store(db_path=Path("index.db"))

# 2. Load CPU-optimized ONNX Text Encoder
model_meta = get_model("mobileclip2-s0")
model_paths = model_meta.download()
text_encoder = TextEncoder(model_paths.text_model_path, model_paths.tokenizer_path)

# 3. Search moments
query = "a red sports car turning at intersection"
results = search(
    query=query,
    store=store,
    text_encoder=text_encoder,
    limit=5,
    max_gap_ms=4000,   # Merge frames within 4.0s gap
    calibrate=True     # Use per-video score baseline calibration
)

# 4. Process segments
for seg in results:
    print(f"Video: {seg.path}")
    print(f"Time Range: {seg.start_ms / 1000.0:.1f}s - {seg.end_ms / 1000.0:.1f}s")
    print(f"Peak Moment: {seg.best_ts_ms / 1000.0:.1f}s")
    print(f"Score: {seg.best_score:.4f} (from {seg.frame_count} frames)\n")
```

---

## 3. Programmatic Indexing

```python
from pathlib import Path
from amonhen.model_registry import get_model
from amonhen.encode import VisionEncoder
from amonhen.store import Store
from amonhen.pipeline import index_videos

store = Store(db_path=Path("index.db"))
model_meta = get_model("mobileclip2-s0")
model_paths = model_meta.download()
vision_encoder = VisionEncoder(model_paths.vision_model_path)

# Index video files
video_files = [Path("footage1.mp4"), Path("footage2.mov")]
indexed_count, total_frames, elapsed_sec = index_videos(
    video_files=video_files,
    store=store,
    vision_encoder=vision_encoder,
    sampler_mode="adaptive",
    dedup_threshold=0.90,
)

print(f"Indexed {indexed_count} video(s), {total_frames} frames in {elapsed_sec:.2f}s")
```

---

## 4. Standalone Vision & Text Embedding Generation

```python
from PIL import Image
from amonhen.model_registry import get_model
from amonhen.encode import VisionEncoder, TextEncoder

model_meta = get_model("mobileclip2-s0")
model_paths = model_meta.download()

vis_encoder = VisionEncoder(model_paths.vision_model_path)
txt_encoder = TextEncoder(model_paths.text_model_path, model_paths.tokenizer_path)

# Embed image
img = Image.open("sample.jpg")
img_vec = vis_encoder.encode_image(img)  # Shape: (512,), L2-normalized

# Embed text
txt_vec = txt_encoder.encode_text("a golden retriever")  # Shape: (512,), L2-normalized

# Compute similarity
similarity = float(img_vec @ txt_vec)
print(f"Cosine Similarity: {similarity:.4f}")
```
