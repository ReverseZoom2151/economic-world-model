"""Compatibility helpers for semantic package moves."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import Any


def _preserve_legacy_symbol_modules(module: ModuleType, legacy_name: str) -> None:
    """Keep function and class identities stable after moving their implementation module."""

    for value in vars(module).values():
        if getattr(value, "__module__", None) != module.__name__:
            continue
        try:
            value.__module__ = legacy_name
        except (AttributeError, TypeError):
            continue


def register_module_aliases(
    package: str,
    aliases: dict[str, str],
    *,
    preserve_symbol_modules: bool = True,
) -> None:
    """Resolve historical child modules to their single canonical implementation modules."""

    for legacy_child, canonical_child in aliases.items():
        legacy_name = f"{package}.{legacy_child}"
        canonical_name = f"{package}.{canonical_child}"
        module = import_module(canonical_name)
        existing: Any = sys.modules.get(legacy_name)
        if existing is not None and existing is not module:
            raise RuntimeError(f"module alias collision for {legacy_name}")
        if preserve_symbol_modules:
            _preserve_legacy_symbol_modules(module, legacy_name)
        sys.modules[legacy_name] = module
