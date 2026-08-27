from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tools.quantize_onnx import quantize_onnx_model


@pytest.fixture
def mock_quant_module():
    mock_module = MagicMock()
    mock_module.QuantType.QInt8 = "QInt8"
    mock_module.QuantType.QUInt8 = "QUInt8"
    with patch.dict(sys.modules, {"onnxruntime.quantization": mock_module}):
        yield mock_module


def test_quantize_onnx_model_executes_dynamic_quant(tmp_path: Path, mock_quant_module):
    in_model = tmp_path / "model.onnx"
    in_model.write_bytes(b"dummy onnx bytes")
    out_model = tmp_path / "output_dir" / "model_quant.onnx"

    res = quantize_onnx_model(in_model, out_model, quant_format="int8")

    assert res == out_model
    assert isinstance(res, Path)
    assert out_model.parent.exists()
    mock_quant_module.quantize_dynamic.assert_called_once_with(
        model_input=str(in_model),
        model_output=str(out_model),
        weight_type=mock_quant_module.QuantType.QInt8,
    )


def test_quantize_onnx_model_respects_format(tmp_path: Path, mock_quant_module):
    in_model = tmp_path / "model.onnx"
    in_model.write_bytes(b"dummy onnx bytes")

    out_int8 = tmp_path / "model_int8.onnx"
    quantize_onnx_model(in_model, out_int8, quant_format="int8")
    mock_quant_module.quantize_dynamic.assert_called_with(
        model_input=str(in_model),
        model_output=str(out_int8),
        weight_type=mock_quant_module.QuantType.QInt8,
    )

    out_uint8 = tmp_path / "model_uint8.onnx"
    quantize_onnx_model(in_model, out_uint8, quant_format="uint8")
    mock_quant_module.quantize_dynamic.assert_called_with(
        model_input=str(in_model),
        model_output=str(out_uint8),
        weight_type=mock_quant_module.QuantType.QUInt8,
    )

    out_upper = tmp_path / "model_upper.onnx"
    quantize_onnx_model(in_model, out_upper, quant_format="INT8")
    mock_quant_module.quantize_dynamic.assert_called_with(
        model_input=str(in_model),
        model_output=str(out_upper),
        weight_type=mock_quant_module.QuantType.QInt8,
    )


def test_quantize_onnx_model_accepts_strings(tmp_path: Path, mock_quant_module):
    in_model = tmp_path / "model.onnx"
    in_model.write_bytes(b"dummy onnx bytes")
    out_model = tmp_path / "str_dir" / "model_quant.onnx"

    res = quantize_onnx_model(str(in_model), str(out_model), quant_format="int8")

    assert res == out_model
    assert isinstance(res, Path)
    assert out_model.parent.exists()
    mock_quant_module.quantize_dynamic.assert_called_with(
        model_input=str(in_model),
        model_output=str(out_model),
        weight_type=mock_quant_module.QuantType.QInt8,
    )
