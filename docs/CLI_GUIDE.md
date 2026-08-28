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
| `list` | List all indexed videos and their stored frame counts |
| `info <video_id>` | Display detailed metadata and baseline score calibration for a video |
| `delete <video_id>`| Remove a video and its stored frame embeddings from the database |
| `setup` | Download and cache official ONNX model weights (~105 MB) |

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
# Basic natural language search
amon-hen search "a dog running on green grass"

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

## 3. Interactive REPL Session

Launch the interactive prompt by running `amon-hen` without arguments:

```bash
amon-hen
```

### REPL Features:
* **Natural Language Queries:** Type any query directly to see instant matching segments and visual score bars.
* **Command History:** Persistent arrow-key history across sessions saved in `~/.amonhen/history`.
* **Slash Commands:**
  * `/open <N>` — Launch the video at the exact start timestamp of result `#N` using your default system player (`mpv`, `vlc`, or `ffplay`).
  * `/help` — Display list of interactive commands and tips.
  * `/exit` or `exit` / `quit` — Exit the interactive session.

---

## 4. Managing Indexed Videos

```bash
# List all indexed videos in the database
amon-hen list

# Inspect video metadata and noise baseline score
amon-hen info 1

# Delete a specific video from the index
amon-hen delete 1
```

---

## 5. Media Player Timestamp Seeking

Amon Hen automatically detects and supports timestamp seeking with:
1. **mpv** (Preferred: `--start=SS.MS`)
2. **VLC** (`--start-time=SS`)
3. **ffplay** (`-ss SS.MS -autoexit`)
