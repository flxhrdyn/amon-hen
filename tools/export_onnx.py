from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_pytorch_model(variant: str) -> Any:
    import open_clip

    # Loads MobileCLIP architecture checkpoint
    model_name = "MobileCLIP-s0" if "s0" in variant else "MobileCLIP-s2"
    model, _, _ = open_clip.create_model_and_transforms(model_name, pretrained=None)
    model.eval()
    return model


def _export_vision(model: Any, out_path: Path, opset: int = 17) -> Path:
    import torch

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_input = torch.randn(1, 3, 256, 256, dtype=torch.float32)

    class VisionWrapper(torch.nn.Module):
        def __init__(self, visual: Any) -> None:
            super().__init__()
            self.visual = visual

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.visual(x)

    wrapper = VisionWrapper(model.visual)
    torch.onnx.export(
        wrapper,
        dummy_input,
        str(out_path),
        input_names=["image"],
        output_names=["embedding"],
        dynamic_axes={"image": {0: "batch_size"}, "embedding": {0: "batch_size"}},
        opset_version=opset,
        do_constant_folding=True,
    )
    return out_path


def _export_text(model: Any, out_path: Path, opset: int = 17) -> Path:
    import torch

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_tokens = torch.zeros(1, 77, dtype=torch.int64)

    class TextWrapper(torch.nn.Module):
        def __init__(self, m: Any) -> None:
            super().__init__()
            self.m = m

        def forward(self, tokens: torch.Tensor) -> torch.Tensor:
            return self.m.encode_text(tokens, normalize=True)

    wrapper = TextWrapper(model)
    torch.onnx.export(
        wrapper,
        dummy_tokens,
        str(out_path),
        input_names=["tokens"],
        output_names=["embedding"],
        dynamic_axes={"tokens": {0: "batch_size"}, "embedding": {0: "batch_size"}},
        opset_version=opset,
        do_constant_folding=True,
    )
    return out_path


def _export_tokenizer(variant: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Writes huggingface tokenizers json
    cfg = {"version": "1.0", "truncation": {"max_length": 77}, "padding": {"length": 77}}
    out_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return out_path


def export_mobileclip_to_onnx(
    model_variant: str, output_dir: Path, opset: int = 17
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model = _load_pytorch_model(model_variant)
    vis = _export_vision(model, output_dir / "vision_model.onnx", opset=opset)
    txt = _export_text(model, output_dir / "text_model.onnx", opset=opset)
    tok = _export_tokenizer(model_variant, output_dir / "tokenizer.json")
    return vis, txt, tok
