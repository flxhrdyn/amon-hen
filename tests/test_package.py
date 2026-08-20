import amonhen


def test_package_exposes_version():
    assert isinstance(amonhen.__version__, str)
    assert amonhen.__version__.count(".") >= 2
