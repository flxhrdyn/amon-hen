from unittest.mock import MagicMock, patch

from amonhen.player import build_player_command, open_video_at


def test_build_player_command_mpv():
    cmd = build_player_command("video.mp4", 12500, player_binary="mpv")
    assert cmd == ["mpv", "--start=12.5", "video.mp4"]


def test_build_player_command_vlc():
    cmd = build_player_command("video.mp4", 12500, player_binary="vlc")
    assert cmd == ["vlc", "--start-time=12.5", "video.mp4"]


def test_build_player_command_ffplay():
    cmd = build_player_command("video.mp4", 12500, player_binary="ffplay")
    assert cmd == ["ffplay", "-ss", "12.5", "-autoexit", "video.mp4"]


def test_build_player_command_auto_detect(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}" if name == "mpv" else None)
    cmd = build_player_command("video.mp4", 1000)
    assert cmd == ["mpv", "--start=1.0", "video.mp4"]


def test_build_player_command_no_player(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    cmd = build_player_command("video.mp4", 1000)
    assert cmd == ["video.mp4"]


def test_open_video_at_nonexistent_returns_false():
    assert open_video_at("nonexistent_file_path_12345.mp4", 1000) is False


def test_open_video_at_existing_file_with_binary(tmp_path):
    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"dummy")

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        success = open_video_at(fake_video, 5000, player_command="mpv")
        assert success is True
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "mpv"
        assert args[1] == "--start=5.0"
        assert str(fake_video) in args[2]


def test_open_video_at_os_fallback_windows(tmp_path, monkeypatch):
    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"dummy")

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("platform.system", lambda: "Windows")
    with patch("os.startfile", create=True) as mock_startfile:
        success = open_video_at(fake_video, 5000)
        assert success is True
        mock_startfile.assert_called_once_with(str(fake_video))


def test_open_video_at_os_fallback_linux(tmp_path, monkeypatch):
    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"dummy")

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    with patch("subprocess.Popen") as mock_popen:
        success = open_video_at(fake_video, 5000)
        assert success is True
        mock_popen.assert_called_once_with(["xdg-open", str(fake_video)])
