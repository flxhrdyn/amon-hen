# Demo

This folder contains two curated sample video clips to try Amon Hen end-to-end:

1. **`amon-hen-speech-demo.webm` (Primary Demo):**
   * *Battle of Amon Hen* (Lord of the Rings: The Fellowship of the Ring, 4:59 full scene).
   * Contains dynamic visual action (sword fights, archers, warriors in forest) and spoken dialogue for hybrid audio & speech retrieval.
   * Source: https://youtu.be/3FWR0frTBn8
2. **`cctv-people-demo.webm` (Surveillance & Desktop Search):**
   * Real-world CCTV street footage for testing pedestrian, umbrella, and vehicle scene retrieval.
   * Source: https://youtu.be/GJNjaRJWVP8

## Try It

### 1. Interactive TUI Mode:
```bash
amon-hen
# Inside TUI:
# swords fight warriors in forest
# /open 1
# a person holding an umbrella
```

### 2. CLI One-Shot Search:
```bash
# Index both demo clips
amon-hen index demo/ --sampler adaptive --db demo/index.db

# Search battle scenes (Amon Hen)
amon-hen search "swords fight warriors in forest" --db demo/index.db
amon-hen search "archer shooting bow" --db demo/index.db

# Search spoken dialogue (Whisper FTS5)
amon-hen search "good time" --db demo/index.db

# Search real-world surveillance events (CCTV)
amon-hen search "a person holding an umbrella" --db demo/index.db
amon-hen search "a car passing by" --db demo/index.db
```

`demo/index.db` is generated locally and gitignored — rerun `index` to recreate it at any time.


