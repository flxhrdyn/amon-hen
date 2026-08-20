"""Pinned identities of the ONNX models AmonHen can use.

The embedding dimension and image size are measured from the actual ONNX
files, never assumed: the store's vector column is declared from embed_dim,
and a mismatch corrupts an index silently rather than loudly.

The default model ships as FP32. An INT8 build was attempted and rejected:
dynamic quantization of this architecture's Conv layers (95 of them, mostly
depthwise/grouped, the bulk of the model's weights) broke the output almost
completely (cosine similarity to FP32 near zero), while quantizing only the
8 MatMul layers left accuracy intact but barely shrank the model. Getting
Conv layers to quantize safely needs static, calibrated quantization with a
real image sample set, which is real measurement work — that belongs in the
Stage 4 benchmark, where the accuracy trade-off can be measured rather than
assumed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    repo_id: str
    vision_file: str
    text_file: str
    tokenizer_file: str
    embed_dim: int
    image_size: int


MOBILECLIP2_S0 = ModelSpec(
    model_id="mobileclip2-s0",
    repo_id="plhery/mobileclip2-onnx",
    vision_file="onnx/s0/vision_model.onnx",
    text_file="onnx/s0/text_model.onnx",
    tokenizer_file="tokenizer.json",
    embed_dim=512,
    image_size=256,
)

DEFAULT_MODEL = MOBILECLIP2_S0

_REGISTRY = {spec.model_id: spec for spec in (MOBILECLIP2_S0,)}


def get_model(model_id: str) -> ModelSpec:
    return _REGISTRY[model_id]
