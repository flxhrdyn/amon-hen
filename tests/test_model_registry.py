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
