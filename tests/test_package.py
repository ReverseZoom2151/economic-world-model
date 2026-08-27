from importlib.metadata import version

import ewm
from ewm import core


def test_package_exposes_version() -> None:
    assert ewm.__version__ == version("economic-world-model")


def test_core_exports_the_documented_world_runtime() -> None:
    assert core.World.__module__ == "ewm.core.world"
