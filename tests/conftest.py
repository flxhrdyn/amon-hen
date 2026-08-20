import subprocess

import imageio_ffmpeg
import pytest


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
