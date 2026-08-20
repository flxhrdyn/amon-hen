# Amon Hen

> *"From the Seat of Seeing, no moment remains hidden."*

Search your video files by describing what's in them, in plain text, entirely on your own CPU.

```
$ amon-hen index ~/videos/
Indexed 12 video(s), 4182 frames in 3m 12s

$ amon-hen search "a person in a yellow helmet"
 1. 00:14:22.3  0.312  warehouse-cam-3.mp4
 2. 01:02:05.1  0.298  warehouse-cam-3.mp4
 3. 00:03:47.8  0.271  site-walkthrough.mp4
```

No GPU, no cloud upload, no server to run. Video stays on your machine.

## Why Amon Hen

Finding a moment in a long video today sits between two extremes. Large vision-language
models (LLaVA-class) need 16 GB+ of VRAM and are too slow to run locally. Naive frame
sampling with no filtering processes thousands of near-identical frames, making indexing
slow and memory-hungry.

Amon Hen fills the gap: a lightweight tool that installs in one command, runs on an
ordinary laptop CPU, and gives results good enough for everyday use. It embeds sampled
frames and text queries into the same vector space with MobileCLIP2 and ranks frames by
cosine similarity, stored in a portable single-file SQLite database via `sqlite-vec`.

The name comes from Amon Hen, the hill with the Seat of Seeing in *The Lord of the
Rings*, where sight opens up across great distance. The metaphor fits: seeing through a
long video's duration to jump straight to one moment.

Built for anyone who keeps long video files on their own machine and wants to search them
without uploading anything, anywhere.

## Install

```bash
uv tool install amonhen
# or
pipx install amonhen
```

The first `index` or `search` downloads the model to `~/.amonhen/models/` (about 285 MB). Run
`amon-hen setup` to fetch it ahead of time.

## Use

```bash
amon-hen index /path/to/video.mp4 --sampler adaptive   # or a directory of videos
amon-hen search "a red car"
amon-hen videos                             # list what's indexed
amon-hen stats                              # index totals, by kept reason
```

Every command supports `--json` for scripting: data goes to stdout, human-readable messages go
to stderr, so output can be piped cleanly.

## What it can and can't find

AmonHen matches **objects and scenes** - "a dog on a couch", "an empty parking lot", "a red car".
It does not understand **actions or events** - "a person entering a room" or "someone falling"
are outside what a single-frame image-text model can do. If your query describes something that
happens over time rather than something visible in a single frame, it will not find it reliably.

## Tested on

Windows x86 and Linux x86, CPU only. No performance or accuracy numbers are published yet -
see [the design spec](docs/superpowers/specs/2026-08-19-amonhen-design.md) for what's measured
so far and what's planned. This project makes no claims about Raspberry Pi, Jetson, or other
edge hardware, because none has been tested.

## Status

Early. Ships the core index/search pipeline (fixed or adaptive frame sampler, FP32
MobileCLIP2). Segment merging, score calibration, benchmark numbers, the interactive
session, and OCR are still to come - see the design spec for the full roadmap.
