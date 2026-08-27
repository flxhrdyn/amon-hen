from __future__ import annotations

from pathlib import Path


def quantize_onnx_model(
    input_onnx_path: str | Path,
    output_onnx_path: str | Path,
    quant_format: str = "int8",
) -> Path:
    """Quantize an ONNX model to 8-bit dynamic quantization for CPU/edge deployment."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    input_path = Path(input_onnx_path)
    output_path = Path(output_onnx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    weight_type = QuantType.QInt8 if quant_format.lower() == "int8" else QuantType.QUInt8

    quantize_dynamic(
        model_input=str(input_path),
        model_output=str(output_path),
        weight_type=weight_type,
    )
    return output_path
