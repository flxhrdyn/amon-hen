# Demo

`cctv-people-demo.webm` is a public CCTV-style clip used to try AmonHen end to end
against real footage, not just synthetic test fixtures. Encoded as VP9/webm, scaled
to 854px wide, audio dropped, to keep the file smaller in the repo.

Source: https://youtu.be/GJNjaRJWVP8

## Try it

### Interactive TUI Mode:
```bash
amon-hen
# Inside TUI:
# /index demo/cctv-people-demo.webm
# a person holding an umbrella
# /open 1
```

### CLI One-Shot Search:
```bash
amon-hen index demo/cctv-people-demo.webm --sampler adaptive --db demo/index.db
amon-hen search "a person holding an umbrella" --db demo/index.db
amon-hen search "a car passing by" --db demo/index.db
```

Real output from this clip:

```text
$ amon-hen index demo/cctv-people-demo.webm --sampler adaptive --db demo/index.db
Indexed 1 video(s), 49 frames in 2.7s

$ amon-hen search "a person holding an umbrella" --db demo/index.db
 1. 00:00:37.0 - 00:01:06.0  0.261  cctv-people-demo.webm
 2. 00:00:02.0 - 00:00:14.0  0.174  cctv-people-demo.webm

$ amon-hen search "a car passing by" --db demo/index.db
 1. 00:00:24.0 - 00:00:32.0  0.227  cctv-people-demo.webm
 2. 00:00:04.0 - 00:00:19.0  0.218  cctv-people-demo.webm
```

`demo/index.db` is generated locally and gitignored - rerun `index` to recreate it.

