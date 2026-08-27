"""Distribution version without importing the public API graph."""

from importlib.metadata import version

__version__ = version("economic-world-model")
