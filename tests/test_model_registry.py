import pytest

from amonhen.model_registry import DEFAULT_MODEL, ModelSpec, get_model


def test_default_model_is_registered():
    assert get_model(DEFAULT_MODEL.model_id) is DEFAULT_MODEL


def test_default_model_fields_are_pinned():
    assert isinstance(DEFAULT_MODEL, ModelSpec)
    assert DEFAULT_MODEL.embed_dim == 512
    assert DEFAULT_MODEL.image_size == 256
    assert DEFAULT_MODEL.vision_file.endswith(".onnx")
    assert DEFAULT_MODEL.text_file.endswith(".onnx")


def test_unknown_model_raises():
    with pytest.raises(KeyError):
        get_model("no-such-model")


def test_default_models_point_to_official_flxhrdyn_namespace():
    s0 = get_model("mobileclip2-s0")
    s2 = get_model("mobileclip2-s2")
    assert s0.repo_id == "flxhrdyn/mobileclip2-s0-onnx"
    assert s2.repo_id == "flxhrdyn/mobileclip2-s2-onnx"
    assert s0.vision_file == "vision_model.onnx"
    assert s0.text_file == "text_model.onnx"
    assert s2.vision_file == "vision_model.onnx"
    assert s2.text_file == "text_model.onnx"
    assert s2.embed_dim == 512
    assert s2.image_size == 256

