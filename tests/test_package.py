from importlib.metadata import version

import ewm


def test_package_exposes_version() -> None:
    assert ewm.__version__ == version("economic-world-model")
