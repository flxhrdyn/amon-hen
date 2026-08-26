# Demo

`cctv-people-demo.webm` is a public CCTV-style clip used to try AmonHen end to end
against real footage, not just synthetic test fixtures. Encoded as VP9/webm, scaled
to 854px wide, audio dropped, to keep the file smaller in the repo.

Source: https://youtu.be/GJNjaRJWVP8

## Try it

```bash
amon-hen index demo/cctv-people-demo.webm --sampler adaptive --db demo/index.db
amon-hen search "a person holding an umbrella" --db demo/index.db
amon-hen search "a car passing by" --db demo/index.db
```

Real output from this clip:

```
$ amon-hen index demo/cctv-people-demo.webm --sampler adaptive --db demo/index.db
Indexed 1 video(s), 49 frames in 2.7s

$ amon-hen search "a person holding an umbrella" --db demo/index.db
 1. 00:01:06.0  0.270  cctv-people-demo.webm
 2. 00:01:05.0  0.266  cctv-people-demo.webm
 3. 00:00:55.0  0.265  cctv-people-demo.webm

$ amon-hen search "a car passing by" --db demo/index.db
 1. 00:00:26.0  0.211  cctv-people-demo.webm
 2. 00:00:28.0  0.208  cctv-people-demo.webm
 3. 00:00:12.0  0.197  cctv-people-demo.webm
```

`demo/index.db` is generated locally and gitignored - rerun `index` to recreate it.
