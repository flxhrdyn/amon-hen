"""
Prepare a Charades-STA subset for benchmarking.

Uses HTTP Range Requests to stream specific MP4 files from the
Charades_v1_480.zip (hosted on AI2 public S3) without downloading
the entire 13 GB archive.

Steps:
  1. Download charades_sta_test.txt from Hugging Face
  2. Parse annotations -> pick N unique video IDs
  3. Fetch ZIP central directory via range request (last 64KB)
  4. Download only the needed MP4 files via per-file range request
  5. Write annotations.json for benchmarks/run.py

Usage:
    uv run python scratch/prepare_charades_sta.py --videos 20 --out benchmarks/charades_sta_subset
"""

from __future__ import annotations

import argparse
import io
import json
import struct
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path


ANNOTATIONS_URL = (
    "https://huggingface.co/datasets/jwnt4/charades-sta-test/resolve/main/"
    "charades_sta_test.txt"
)
ZIP_URL = "https://ai2-public-datasets.s3-us-west-2.amazonaws.com/charades/Charades_v1_480.zip"


# ---------------------------------------------------------------------------
# Helper: HTTP range request
# ---------------------------------------------------------------------------

def http_get_range(url: str, start: int, end: int) -> bytes:
    """Download bytes [start, end] (inclusive) via HTTP Range."""
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def get_content_length(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as resp:
        cl = resp.headers.get("Content-Length")
        if cl:
            return int(cl)
    raise RuntimeError(f"Cannot determine content-length for {url}")


# ---------------------------------------------------------------------------
# Parse ZIP central directory from the end of the file
# ---------------------------------------------------------------------------

def find_zip_entries(url: str, zip_size: int, tail_size: int = 131072) -> dict[str, tuple[int, int]]:
    """
    Returns {filename: (offset_in_zip, compressed_size)} for all entries.
    Handles both standard and ZIP64 archives via HTTP range requests.
    """
    tail_start = max(0, zip_size - tail_size)
    tail = http_get_range(url, tail_start, zip_size - 1)

    ZIP64_LOCATOR_SIG = b"\x50\x4b\x06\x07"
    ZIP64_EOCD_SIG    = b"\x50\x4b\x06\x06"
    EOCD_SIG          = b"\x50\x4b\x05\x06"

    cd_offset: int = 0
    cd_size: int = 0

    # Try ZIP64 first
    loc_pos = tail.rfind(ZIP64_LOCATOR_SIG)
    if loc_pos >= 0:
        eocd64_abs_offset = struct.unpack_from("<Q", tail, loc_pos + 8)[0]
        eocd64_tail_offset = eocd64_abs_offset - tail_start
        if 0 <= eocd64_tail_offset < len(tail):
            eocd64 = tail[eocd64_tail_offset:]
        else:
            eocd64 = http_get_range(url, eocd64_abs_offset, eocd64_abs_offset + 55)
        if eocd64[:4] == ZIP64_EOCD_SIG:
            cd_size   = struct.unpack_from("<Q", eocd64, 40)[0]
            cd_offset = struct.unpack_from("<Q", eocd64, 48)[0]
            print(f"  ZIP64 detected. cd_offset={cd_offset:,} cd_size={cd_size:,}")

    if cd_offset == 0:
        pos = tail.rfind(EOCD_SIG)
        if pos < 0:
            raise RuntimeError("Could not find EOCD signature in ZIP tail.")
        eocd = tail[pos:]
        cd_size   = struct.unpack_from("<I", eocd, 12)[0]
        cd_offset = struct.unpack_from("<I", eocd, 16)[0]
        print(f"  Standard ZIP. cd_offset={cd_offset:,} cd_size={cd_size:,}")

    print(f"  ZIP total size: {zip_size:,} bytes")

    # Download central directory
    cd_data = http_get_range(url, cd_offset, cd_offset + cd_size - 1)

    # Parse central directory entries (handle ZIP64 extra fields)
    entries: dict[str, tuple[int, int]] = {}
    idx = 0
    CD_SIG = b"\x50\x4b\x01\x02"
    ZIP64_EXTRA_ID = 0x0001
    while idx < len(cd_data):
        if cd_data[idx: idx + 4] != CD_SIG:
            break
        # Standard 32-bit fields (may be 0xFFFFFFFF for ZIP64)
        orig_size_32  = struct.unpack_from("<I", cd_data, idx + 24)[0]
        comp_size_32  = struct.unpack_from("<I", cd_data, idx + 20)[0]
        local_off_32  = struct.unpack_from("<I", cd_data, idx + 42)[0]
        fname_len     = struct.unpack_from("<H", cd_data, idx + 28)[0]
        extra_len     = struct.unpack_from("<H", cd_data, idx + 30)[0]
        comment_len   = struct.unpack_from("<H", cd_data, idx + 32)[0]

        fname = cd_data[idx + 46: idx + 46 + fname_len].decode("utf-8", errors="replace")

        # Parse extra field for ZIP64 values
        comp_size   = comp_size_32
        local_offset = local_off_32
        if extra_len > 0:
            extra_start = idx + 46 + fname_len
            ex_idx = extra_start
            while ex_idx < extra_start + extra_len - 3:
                ex_id   = struct.unpack_from("<H", cd_data, ex_idx)[0]
                ex_size = struct.unpack_from("<H", cd_data, ex_idx + 2)[0]
                if ex_id == ZIP64_EXTRA_ID:
                    ex_data = cd_data[ex_idx + 4: ex_idx + 4 + ex_size]
                    off = 0
                    # Fields present only when standard value == 0xFFFFFFFF
                    if orig_size_32 == 0xFFFFFFFF and off + 8 <= len(ex_data):
                        off += 8  # original size (skip)
                    if comp_size_32 == 0xFFFFFFFF and off + 8 <= len(ex_data):
                        comp_size = struct.unpack_from("<Q", ex_data, off)[0]
                        off += 8
                    if local_off_32 == 0xFFFFFFFF and off + 8 <= len(ex_data):
                        local_offset = struct.unpack_from("<Q", ex_data, off)[0]
                        off += 8
                    break
                ex_idx += 4 + ex_size

        entries[fname] = (local_offset, comp_size)
        idx += 46 + fname_len + extra_len + comment_len


    print(f"  Found {len(entries)} entries in ZIP central directory.")
    return entries


def download_zip_entry(url: str, zip_entries: dict[str, tuple[int, int]], filename: str, out_path: Path) -> bool:
    """
    Download a single file from the remote ZIP using range requests.
    The local file header must be skipped to reach actual data.
    """
    if out_path.exists() and out_path.stat().st_size > 10_000:
        return True

    local_offset, comp_size = zip_entries[filename]

    # Read local file header to find actual data start
    # Local header: 30 bytes + fname_len + extra_len
    header_data = http_get_range(url, local_offset, local_offset + 29)
    if header_data[:4] != b"\x50\x4b\x03\x04":
        print(f"  ERROR: Bad local header signature for {filename}")
        return False

    fname_len = struct.unpack_from("<H", header_data, 26)[0]
    extra_len = struct.unpack_from("<H", header_data, 28)[0]
    data_start = local_offset + 30 + fname_len + extra_len

    print(f"  Downloading {filename} ({comp_size / 1_048_576:.1f} MB)...")
    data = http_get_range(url, data_start, data_start + comp_size - 1)

    # Check if data is compressed (method != 0)
    method = struct.unpack_from("<H", header_data, 8)[0]
    if method == 8:
        import zlib
        data = zlib.decompress(data, -15)
    elif method != 0:
        print(f"  ERROR: Unsupported compression method {method} for {filename}")
        return False

    out_path.write_bytes(data)
    if out_path.stat().st_size < 10_000:
        out_path.unlink(missing_ok=True)
        return False
    return True


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------

def download_annotations(cache_path: Path) -> str:
    if cache_path.exists():
        print(f"Using cached annotations: {cache_path}")
        return cache_path.read_text(encoding="utf-8")
    print("Downloading Charades-STA annotations from Hugging Face...")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ANNOTATIONS_URL, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    cache_path.write_text(text, encoding="utf-8")
    print(f"Saved to {cache_path}")
    return text


def parse_annotations(text: str) -> dict[str, list[tuple[float, float, str]]]:
    result: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            meta, query = line.split("##", 1)
            parts = meta.strip().split()
            vid, start_s, end_s = parts[0], float(parts[1]), float(parts[2])
            result[vid].append((start_s, end_s, query.strip()))
        except Exception:
            continue
    return result


def get_video_duration(video_path: Path) -> float:
    import subprocess, json as _json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        data = _json.loads(result.stdout)
        dur = data.get("format", {}).get("duration")
        if dur:
            return float(dur)
    except Exception as e:
        print(f"  WARN: ffprobe failed for {video_path.name}: {e}")
    return 30.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", type=int, default=20)
    parser.add_argument("--out", type=Path, default=Path("benchmarks/charades_sta_subset"))
    args = parser.parse_args()

    out_dir: Path = args.out
    video_dir = out_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)

    # 1. Annotations
    ann_cache = out_dir / "charades_sta_test.txt"
    raw_text = download_annotations(ann_cache)
    per_video = parse_annotations(raw_text)
    print(f"Total unique video IDs in Charades-STA test: {len(per_video)}")

    # 2. Get ZIP central directory
    print(f"\nProbing ZIP at {ZIP_URL} ...")
    try:
        zip_size = get_content_length(ZIP_URL)
        print(f"ZIP size: {zip_size / 1_073_741_824:.2f} GB")
        zip_entries = find_zip_entries(ZIP_URL, zip_size)
    except Exception as e:
        print(f"ERROR: Could not access ZIP central directory: {e}")
        print("The AI2 S3 bucket may not support range requests or the URL has changed.")
        return

    # Map video_id -> zip entry name
    # Charades zip contains files like "XXXXX.mp4" or "Charades_v1_480/XXXXX.mp4"
    # Build a lookup
    zip_name_lookup: dict[str, str] = {}
    for entry_name in zip_entries:
        stem = Path(entry_name).stem
        zip_name_lookup[stem] = entry_name

    # 3. Pick video IDs present in ZIP
    video_ids = list(per_video.keys())
    selected: list[str] = []
    for vid in video_ids:
        if vid in zip_name_lookup:
            selected.append(vid)
        if len(selected) >= args.videos:
            break

    if not selected:
        print("\nERROR: None of the Charades-STA video IDs found in the ZIP central directory.")
        print("Available example entries:", list(zip_entries.keys())[:5])
        return

    print(f"\nFound {len(selected)} matchable videos. Downloading...")

    # 4. Download and build manifest
    manifest = []
    for vid_id in selected:
        entry_name = zip_name_lookup[vid_id]
        out_path = video_dir / f"{vid_id}.mp4"
        try:
            ok = download_zip_entry(ZIP_URL, zip_entries, entry_name, out_path)
        except Exception as e:
            print(f"  ERROR downloading {vid_id}: {e}")
            ok = False

        if not ok:
            print(f"  SKIP: {vid_id}")
            continue

        duration_s = get_video_duration(out_path)
        annotations = [
            {"query": q, "start_s": s, "end_s": e}
            for s, e, q in per_video[vid_id]
            if e <= duration_s + 2.0
        ]
        if not annotations:
            print(f"  SKIP: {vid_id} has no valid annotations (duration={duration_s:.1f}s)")
            continue

        manifest.append({
            "video_path": f"videos/{vid_id}.mp4",
            "duration_s": duration_s,
            "annotations": annotations,
        })
        print(f"  OK: {vid_id} ({duration_s:.1f}s, {len(annotations)} annotations)")

    # 5. Write annotations.json
    ann_out = out_dir / "annotations.json"
    ann_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDone. {len(manifest)} videos ready.")
    print(f"Annotations: {ann_out}")
    if manifest:
        total_ann = sum(len(m["annotations"]) for m in manifest)
        print(f"Total annotation queries: {total_ann}")
        print(f"\nRun benchmark with:")
        print(f"  uv run python -m benchmarks.run --data-dir {out_dir}")
    else:
        print("No videos were successfully prepared.")


if __name__ == "__main__":
    main()
