# AmonHen

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
amon-hen index /path/to/video.mp4          # or a directory of videos
amon-hen search "a red car"
amon-hen videos                             # list what's indexed
amon-hen stats                              # index totals
```

Every command supports `--json` for scripting: data goes to stdout, human-readable messages go
to stderr, so output can be piped cleanly.

## What it can and can't find

AmonHen matches **objects and scenes** — "a dog on a couch", "an empty parking lot", "a red car".
It does not understand **actions or events** — "a person entering a room" or "someone falling"
are outside what a single-frame image-text model can do. If your query describes something that
happens over time rather than something visible in a single frame, it will not find it reliably.

## Tested on

Windows x86 and Linux x86, CPU only. No performance or accuracy numbers are published yet —
see [the design spec](docs/superpowers/specs/2026-08-19-amonhen-design.md) for what's measured
so far and what's planned. This project makes no claims about Raspberry Pi, Jetson, or other
edge hardware, because none has been tested.

## Status

Early. This ships the core index/search pipeline on a fixed-rate frame sampler and an FP32
MobileCLIP2 model. The adaptive sampler, segment merging, score calibration, benchmark numbers,
the interactive session, and OCR are still to come — see the design spec for the full roadmap.
