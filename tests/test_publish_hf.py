from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tools.publish_to_hf import generate_model_card, publish_model_package


def test_generate_model_card_contains_metadata():
    card = generate_model_card("mobileclip2-s0", min_cosine=0.9998, latency_ms=25.4)
    assert "mobileclip2-s0" in card
    assert "0.9998" in card
    assert "25.4" in card
    assert "Amon Hen" in card or "amon-hen" in card
    assert "license: mit" in card
    assert "tags:" in card
    assert "onnx" in card


def test_generate_model_card_custom_variant():
    card = generate_model_card("mobileclip2-s2", min_cosine=0.9999, latency_ms=45.2)
    assert "mobileclip2-s2" in card
    assert "0.9999" in card
    assert "45.2" in card


def test_publish_model_package_calls_hf_api(tmp_path: Path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "README.md").write_text("Model card", encoding="utf-8")

    with patch("huggingface_hub.HfApi") as mock_hf:
        mock_api = MagicMock()
        mock_hf.return_value = mock_api

        url = publish_model_package("flxhrdyn/mobileclip2-s0-onnx", pkg_dir, token="test_token")
        assert "flxhrdyn/mobileclip2-s0-onnx" in url
        mock_hf.assert_called_once_with(token="test_token")
        mock_api.create_repo.assert_called_once_with(
            repo_id="flxhrdyn/mobileclip2-s0-onnx", exist_ok=True, repo_type="model"
        )
        assert mock_api.upload_folder.called
        call_kwargs = mock_api.upload_folder.call_args.kwargs
        assert call_kwargs["folder_path"] == str(pkg_dir)
        assert call_kwargs["repo_id"] == "flxhrdyn/mobileclip2-s0-onnx"
        assert call_kwargs["repo_type"] == "model"


def test_publish_model_package_uses_env_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "README.md").write_text("Model card", encoding="utf-8")
    monkeypatch.setenv("HF_TOKEN", "env_secret_token")

    with patch("huggingface_hub.HfApi") as mock_hf:
        mock_api = MagicMock()
        mock_hf.return_value = mock_api

        url = publish_model_package("flxhrdyn/mobileclip2-s2-onnx", pkg_dir)
        assert url == "https://huggingface.co/flxhrdyn/mobileclip2-s2-onnx"
        mock_hf.assert_called_once_with(token="env_secret_token")


def test_publish_model_package_validates_package_dir(tmp_path: Path):
    non_existent = tmp_path / "non_existent_pkg"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        publish_model_package("flxhrdyn/mobileclip2-s0-onnx", non_existent)


def test_publish_model_package_validates_repo_id(tmp_path: Path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    with pytest.raises(ValueError, match="repo_id cannot be empty"):
        publish_model_package("", pkg_dir)
