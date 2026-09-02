# Amon Hen CLI Guide

Complete reference manual for using the **Amon Hen** command-line interface.

---

## Command Overview

```
amon-hen [COMMAND] [OPTIONS]
```

If run with no arguments, `amon-hen` automatically launches the **Interactive REPL Session**.

| Command | Description |
| :--- | :--- |
| `index <paths...>` | Extract, filter, and embed video frames into the local database |
| `search <query>` | Query video moments using natural language descriptions |
| `cut <video> -s <start> -e <end>` | Extract a video segment into a standalone video clip |
| `videos` | List all indexed videos and their stored frame counts |
| `stats` | Display database totals and gate filtering statistics |
| `setup` | Download and cache official ONNX model weights (approx. 105 MB) |
| `version` | Print current package version |


---

## 1. Indexing Videos (`amon-hen index`)

Extract and store frame embeddings for one or more video files or directories:

```bash
# Index a single video file
amon-hen index video.mp4

# Index multiple video files
amon-hen index clip1.mp4 clip2.mkv clip3.mov

# Recursively index an entire folder of videos
amon-hen index /path/to/video_folder/ --recursive

# Index using a custom SQLite database location
amon-hen index footage.mp4 --db /path/to/custom_index.db
```

### Sampler Options
* `--sampler adaptive` (*Default & Recommended*): Three-gate motion-based frame sampling. Dynamically samples when visual change occurs, skips redundant frames via perceptual hashing, drops blurry frames, and dedupes adjacent embeddings (up to **7.8x faster** and **70% less storage**).
* `--sampler fixed`: Fixed uniform sampling (e.g. 1 frame every second).
* `--fps <float>`: Target frame extraction rate for fixed sampling (default: `1.0`).
* `--threshold <float>`: Motion sensitivity threshold for adaptive sampling (default: `30.0`).
* `--dedup-threshold <float>`: Cosine similarity threshold for deduplicating adjacent frames (default: `0.90`).

---

## 2. Searching Moments (`amon-hen search`)

Retrieve relevant video moments using natural language:

```bash
# Basic natural language search (searches visual scenes + spoken dialogue)
amon-hen search "a dog running on green grass"

# Specific retrieval mode: hybrid (default), visual-only, or speech-only
amon-hen search "hello everyone" --mode speech
amon-hen search "red sports car" --mode visual
amon-hen search "presentation slides" --mode hybrid

# Return top 5 results (default: 10)
amon-hen search "person entering red car" --limit 5

# Adjust temporal segment merge gap (default: 4.0 seconds)
amon-hen search "whiteboard presentation" --merge-gap 6.0

# Set a manual minimum similarity score cutoff (0.0 to 1.0)
amon-hen search "night driving scene" --min-score 0.22

# Output machine-readable JSON (useful for piping into scripts/tools)
amon-hen search "forklift lifting crate" --json
```


---

## 3. Cutting Video Segments (`amon-hen cut`)

Extract matching moments or arbitrary timestamp ranges into standalone video clips:

```bash
# Lossless stream-copy extraction (instantaneous, < 0.2s)
amon-hen cut video.mp4 --start 00:01:15 --end 00:01:40

# Custom output destination
amon-hen cut footage.mp4 -s 75.5 -e 90.0 -o highlight.mp4

# Frame-accurate re-encoded export (libx264/aac)
amon-hen cut clip.mkv --start 00:00:10.5 --end 00:00:25.0 --reencode

# Machine-readable JSON output
amon-hen cut video.mp4 -s 00:10 -e 00:20 --json
```

### Options:
* `-s, --start <time>`: Start timestamp in seconds (`75.5`) or formatted time (`01:15.5`, `00:01:15`).
* `-e, --end <time>`: End timestamp in seconds or formatted time.
* `-o, --output <path>`: Destination path (default: `<video_stem>_clip_<start>_<end>.mp4`).
* `--reencode`: Re-encode video and audio streams for exact non-keyframe cuts.
* `--json`: Output structured JSON metadata to `stdout`.

---

## 4. Interactive REPL Session

Launch the interactive prompt by running `amon-hen` without arguments:

```bash
amon-hen
```

### REPL Features:
* **Natural Language Queries:** Type any query directly to see instant matching segments and visual score bars.
* **Command History:** Persistent arrow-key history across sessions saved in `~/.amonhen/history`.
* **Slash Commands:**
  * `/open <N>` (or `/<N>`): Launch the video at the exact start timestamp of result `#N` using your default system player (`mpv`, `vlc`, or `ffplay`).
  * `/cut <N> [output.mp4]`: Export result `#N` directly to a video clip. Single-frame detections automatically receive +/- 2.0s padding.
  * `/videos`: List all indexed videos and frame counts.
  * `/stats`: Display indexing totals and sampler gate statistics.
  * `/help`: Display list of interactive commands and tips.
  * `/exit` or `/quit`: Exit the interactive session.



---

## 5. Managing Indexed Videos & Statistics

```bash
# List all indexed videos, durations, and stored frame counts
amon-hen videos

# Inspect indexing breakdown across sampler gates
amon-hen stats

# Output raw JSON for pipeline automation
amon-hen videos --json
amon-hen stats --json
```

---

## 6. Media Player Timestamp Seeking

Amon Hen automatically detects and supports timestamp seeking with:
1. **mpv** (Preferred: `--start=SS.MS`)
2. **VLC** (`--start-time=SS`)
3. **ffplay** (`-ss SS.MS -autoexit`)

