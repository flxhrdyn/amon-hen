from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.export_onnx import (
    _export_text,
    _export_tokenizer,
    _export_vision,
    _load_pytorch_model,
    export_mobileclip_to_onnx,
)


def test_export_mobileclip_to_onnx_creates_files(tmp_path: Path):
    with (
        patch("tools.export_onnx._load_pytorch_model") as mock_load,
        patch("tools.export_onnx._export_vision") as mock_vis,
        patch("tools.export_onnx._export_text") as mock_txt,
        patch("tools.export_onnx._export_tokenizer") as mock_tok,
    ):
        mock_load.return_value = MagicMock()
        mock_vis.return_value = tmp_path / "vision_model.onnx"
        mock_txt.return_value = tmp_path / "text_model.onnx"
        mock_tok.return_value = tmp_path / "tokenizer.json"

        vis, txt, tok = export_mobileclip_to_onnx("mobileclip2-s0", tmp_path)
        assert vis.name == "vision_model.onnx"
        assert txt.name == "text_model.onnx"
        assert tok.name == "tokenizer.json"
        mock_load.assert_called_once_with("mobileclip2-s0")
        mock_vis.assert_called_once()
        mock_txt.assert_called_once()
        mock_tok.assert_called_once_with("mobileclip2-s0", tmp_path / "tokenizer.json")


def test_export_tokenizer_creates_json_config(tmp_path: Path):
    out_file = tmp_path / "tokenizer.json"
    result = _export_tokenizer("mobileclip2-s0", out_file)
    assert result == out_file
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["version"] == "1.0"
    assert data["truncation"]["max_length"] == 77
    assert data["padding"]["length"] == 77


def test_load_pytorch_model_invokes_open_clip():
    mock_open_clip = MagicMock()
    mock_model = MagicMock()
    mock_open_clip.create_model_and_transforms.return_value = (mock_model, None, None)

    with patch.dict(sys.modules, {"open_clip": mock_open_clip}):
        model_s0 = _load_pytorch_model("mobileclip2-s0")
        assert model_s0 == mock_model
        mock_open_clip.create_model_and_transforms.assert_called_with(
            "MobileCLIP-s0", pretrained=None
        )
        mock_model.eval.assert_called()

        model_s2 = _load_pytorch_model("mobileclip2-s2")
        assert model_s2 == mock_model
        mock_open_clip.create_model_and_transforms.assert_called_with(
            "MobileCLIP-s2", pretrained=None
        )


def test_export_vision_calls_torch_onnx_export(tmp_path: Path):
    mock_torch = MagicMock()
    with patch.dict(sys.modules, {"torch": mock_torch}):
        mock_model = MagicMock()
        out_path = tmp_path / "vision" / "vision_model.onnx"
        res = _export_vision(mock_model, out_path, opset=17)
        assert res == out_path
        mock_torch.onnx.export.assert_called_once()
        args, kwargs = mock_torch.onnx.export.call_args
        assert kwargs["input_names"] == ["image"]
        assert kwargs["output_names"] == ["embedding"]
        assert kwargs["opset_version"] == 17
        assert kwargs["do_constant_folding"] is True


def test_export_text_calls_torch_onnx_export(tmp_path: Path):
    mock_torch = MagicMock()
    with patch.dict(sys.modules, {"torch": mock_torch}):
        mock_model = MagicMock()
        out_path = tmp_path / "text" / "text_model.onnx"
        res = _export_text(mock_model, out_path, opset=17)
        assert res == out_path
        mock_torch.onnx.export.assert_called_once()
        args, kwargs = mock_torch.onnx.export.call_args
        assert kwargs["input_names"] == ["tokens"]
        assert kwargs["output_names"] == ["embedding"]
        assert kwargs["opset_version"] == 17
        assert kwargs["do_constant_folding"] is True
