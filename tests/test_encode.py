import numpy as np
import pytest

from amonhen.encode import ImageEncoder, TextEncoder
from amonhen.model_registry import DEFAULT_MODEL


class FakeSession:
    """Stands in for onnxruntime.InferenceSession.

    Returns a deterministic non-normalised vector per input row so the
    test can assert that the encoder, not the model, does the
    normalisation.
    """

    def __init__(self, embed_dim: int, input_name: str = "input"):
        self.embed_dim = embed_dim
        self.input_name = input_name
        self.calls: list[np.ndarray] = []

    def get_inputs(self):
        class _In:
            name = self.input_name

        return [_In()]

    def get_outputs(self):
        class _Out:
            name = "output"

        return [_Out()]

    def run(self, _outputs, feed):
        batch = next(iter(feed.values()))
        self.calls.append(batch)
        n = batch.shape[0]
        out = np.tile(np.arange(self.embed_dim, dtype=np.float32), (n, 1))
        return [out * 3.0]


def test_image_encoder_returns_normalised_batch():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)
    images = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(3)]

    vectors = encoder.embed(images)

    assert vectors.shape == (3, DEFAULT_MODEL.embed_dim)
    assert vectors.dtype == np.float32
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_image_encoder_sends_one_batch_not_one_call_per_image():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    encoder.embed([np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(4)])

    assert len(fake.calls) == 1
    assert fake.calls[0].shape[0] == 4


def test_image_encoder_preprocesses_to_model_input_shape():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    encoder.embed([np.zeros((64, 48, 3), dtype=np.uint8)])

    batch = fake.calls[0]
    size = DEFAULT_MODEL.image_size
    assert batch.shape == (1, 3, size, size)
    assert batch.dtype == np.float32


def test_preprocessing_center_crops_instead_of_squashing():
    """MobileCLIP2 was trained on shortest-edge resize plus a centre crop.

    Stretching a 16:9 frame into a square feeds the model geometry it has
    never seen, shifting every frame embedding.
    """
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    # A wide frame whose edges differ from its centre. A centre crop keeps
    # only the middle band; a squash drags the edges into view.
    wide = np.zeros((90, 320, 3), dtype=np.uint8)
    wide[:, :100] = 255
    wide[:, 220:] = 255

    encoder.embed([wide])

    assert fake.calls[0].max() == 0.0


def test_empty_batch_returns_empty_array_without_calling_the_model():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = ImageEncoder(DEFAULT_MODEL, session_factory=lambda spec: fake)

    vectors = encoder.embed([])

    assert vectors.shape == (0, DEFAULT_MODEL.embed_dim)
    assert fake.calls == []


def test_text_encoder_returns_single_normalised_vector():
    fake = FakeSession(DEFAULT_MODEL.embed_dim)
    encoder = TextEncoder(
        DEFAULT_MODEL,
        session_factory=lambda spec: fake,
        tokenizer=lambda text: np.zeros((1, 77), dtype=np.int64),
    )

    vector = encoder.embed("a person in a yellow helmet")

    assert vector.shape == (DEFAULT_MODEL.embed_dim,)
    assert vector.dtype == np.float32
    assert np.isclose(np.linalg.norm(vector), 1.0, atol=1e-5)


@pytest.mark.slow
def test_real_model_produces_higher_similarity_for_matching_text():
    """Sanity check against the real model. Skipped by default."""
    image_encoder = ImageEncoder()
    text_encoder = TextEncoder()

    red = np.zeros((256, 256, 3), dtype=np.uint8)
    red[:, :, 0] = 220
    blue = np.zeros((256, 256, 3), dtype=np.uint8)
    blue[:, :, 2] = 220

    vectors = image_encoder.embed([red, blue])
    query = text_encoder.embed("a solid red image")

    assert float(vectors[0] @ query) > float(vectors[1] @ query)
