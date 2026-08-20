import subprocess

import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope="session")
def ffmpeg_bin() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory, ffmpeg_bin) -> str:
    """A 4-second 32x32 test pattern at 10 fps: 40 frames, known duration."""
    path = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run(
        [
            ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=32x32:rate=10:duration=4",
            "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )
    return str(path)


@pytest.fixture(scope="session")
def static_video(tmp_path_factory, ffmpeg_bin) -> str:
    """A 2-second video of one unchanging, detailed frame.

    Detailed enough to clear the blur gate, unchanging enough that the
    dedup gate should collapse it to a single kept frame.
    """
    directory = tmp_path_factory.mktemp("static")
    still = directory / "still.png"
    path = directory / "static.mp4"

    rng = np.random.default_rng(11)
    Image.fromarray(rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)).save(still)

    subprocess.run(
        [
            ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(still), "-t", "2", "-r", "10",
            "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )
    return str(path)
