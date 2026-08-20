import numpy as np
import pytest

from amonhen.sample import AdaptiveSampler, FixedSampler, build_sampler


def frame(value: int) -> np.ndarray:
    return np.full((16, 16, 3), value, dtype=np.uint8)


def sharp_frame(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(16, 16, 3), dtype=np.uint8)


def test_fixed_sampler_keeps_every_frame():
    sampler = FixedSampler(fps=1.0)

    assert all(sampler.keep(frame(value)) for value in (0, 0, 255))


def test_fixed_sampler_reports_its_reason():
    assert FixedSampler(fps=1.0).reason == "fixed"


def test_config_hash_changes_with_fps():
    assert FixedSampler(fps=1.0).config_hash() != FixedSampler(fps=2.0).config_hash()


def test_config_hash_is_stable_for_equal_settings():
    assert FixedSampler(fps=1.0).config_hash() == FixedSampler(fps=1.0).config_hash()


def test_build_sampler_returns_fixed():
    assert isinstance(build_sampler("fixed", fps=1.0), FixedSampler)


def test_build_sampler_rejects_unknown_name():
    with pytest.raises(ValueError):
        build_sampler("nonexistent", fps=1.0)


def test_adaptive_sampler_keeps_first_frame():
    sampler = AdaptiveSampler(fps=1.0)

    assert sampler.keep(sharp_frame(1)) is True


def test_adaptive_sampler_drops_near_duplicate_frame():
    sampler = AdaptiveSampler(fps=1.0)
    sampler.keep(frame(100))

    assert sampler.keep(frame(101)) is False


def test_adaptive_sampler_keeps_a_visually_different_frame():
    sampler = AdaptiveSampler(fps=1.0)
    sampler.keep(sharp_frame(1))

    assert sampler.keep(sharp_frame(2)) is True


def test_adaptive_sampler_drops_a_blurry_flat_frame():
    sampler = AdaptiveSampler(fps=1.0)
    sampler.keep(sharp_frame(1))

    assert sampler.keep(frame(50)) is False


def test_adaptive_sampler_reports_its_reason():
    assert AdaptiveSampler(fps=1.0).reason == "adaptive"


def test_adaptive_config_hash_differs_from_fixed():
    assert AdaptiveSampler(fps=1.0).config_hash() != FixedSampler(fps=1.0).config_hash()


def test_build_sampler_returns_adaptive():
    assert isinstance(build_sampler("adaptive", fps=1.0), AdaptiveSampler)
