import numpy as np
import pytest

from amonhen.sample import FixedSampler, build_sampler


def frame(value: int) -> np.ndarray:
    return np.full((16, 16, 3), value, dtype=np.uint8)


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
        build_sampler("adaptive", fps=1.0)
