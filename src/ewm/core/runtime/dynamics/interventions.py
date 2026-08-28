"""Atomic interventions with canonical before-and-after provenance."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from ...domain.definition import WorldComponent
from ...domain.records import freeze_value, thaw_value
from ...provenance.serialization import content_digest

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _json_pointer_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


@dataclass(frozen=True, slots=True)
class InterventionTarget:
    """A world component and nested mapping path selected for replacement."""

    component: WorldComponent
    path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.component, WorldComponent):
            raise ValueError("intervention component is unsupported")
        path = tuple(self.path)
        if any(not segment for segment in path):
            raise ValueError("intervention path segments must not be empty")
        object.__setattr__(self, "path", path)

    @property
    def json_pointer(self) -> str:
        """RFC 6901-style pointer for the component-relative target."""

        parts = (self.component.value, *self.path)
        return "/" + "/".join(_json_pointer_segment(part) for part in parts)


class InterventionOperation(StrEnum):
    """The fail-closed operation currently supported by core interventions."""

    REPLACE = "replace"


@dataclass(frozen=True, slots=True)
class InterventionDiff:
    """Machine-readable record of one atomic replacement."""

    operation: InterventionOperation
    path: str
    before: Any
    after: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "before", freeze_value(self.before))
        object.__setattr__(self, "after", freeze_value(self.after))

    def as_data(self) -> Mapping[str, Any]:
        """Return a canonical JSON-Patch-like mapping."""

        return cast(
            Mapping[str, Any],
            freeze_value(
                {
                    "op": self.operation.value,
                    "path": self.path,
                    "before": self.before,
                    "after": self.after,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class SetValueIntervention:
    """A compare-and-set replacement of one existing model value."""

    name: str
    target: InterventionTarget
    replacement: Any
    expected_before_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("intervention name must not be empty")
        if self.expected_before_sha256 is not None and not _SHA256_PATTERN.fullmatch(
            self.expected_before_sha256
        ):
            raise ValueError("expected_before_sha256 must be 64 lowercase hexadecimal characters")
        content_digest(self.replacement)
        object.__setattr__(self, "replacement", freeze_value(self.replacement))


@dataclass(frozen=True, slots=True)
class InterventionRecord:
    """Canonical provenance for one successfully applied intervention."""

    name: str
    target: InterventionTarget
    before_sha256: str
    after_sha256: str
    target_before_sha256: str
    target_after_sha256: str
    diff: InterventionDiff


@dataclass(frozen=True, slots=True)
class InterventionApplication:
    """An immutable transformed subject and the record that certifies it."""

    subject: Mapping[str, Any]
    record: InterventionRecord

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", freeze_value(self.subject))


def _locate_parent(
    subject: dict[str, Any],
    path: tuple[str, ...],
    *,
    pointer: str,
) -> tuple[dict[str, Any], str]:
    parent = subject
    for segment in path[:-1]:
        if segment not in parent or not isinstance(parent[segment], dict):
            raise KeyError(f"intervention target {pointer!r} does not exist")
        parent = cast(dict[str, Any], parent[segment])
    key = path[-1]
    if key not in parent:
        raise KeyError(f"intervention target {pointer!r} does not exist")
    return parent, key


def apply_intervention(
    subject: Mapping[str, Any],
    intervention: SetValueIntervention,
) -> InterventionApplication:
    """Apply a replacement to an owned copy after all preconditions pass."""

    before_sha256 = content_digest(subject)
    mutable = thaw_value(subject)
    if not isinstance(mutable, dict):
        raise TypeError("intervention subject must be a mapping")
    full_path = (intervention.target.component.value, *intervention.target.path)
    parent, key = _locate_parent(
        cast(dict[str, Any], mutable),
        full_path,
        pointer=intervention.target.json_pointer,
    )
    before = parent[key]
    target_before_sha256 = content_digest(before)
    expected = intervention.expected_before_sha256
    if expected is not None and target_before_sha256 != expected:
        raise ValueError("intervention precondition hash does not match target")
    after = thaw_value(intervention.replacement)
    parent[key] = after
    frozen_subject = cast(Mapping[str, Any], freeze_value(mutable))
    after_sha256 = content_digest(frozen_subject)
    diff = InterventionDiff(
        operation=InterventionOperation.REPLACE,
        path=intervention.target.json_pointer,
        before=before,
        after=after,
    )
    return InterventionApplication(
        subject=frozen_subject,
        record=InterventionRecord(
            name=intervention.name,
            target=intervention.target,
            before_sha256=before_sha256,
            after_sha256=after_sha256,
            target_before_sha256=target_before_sha256,
            target_after_sha256=content_digest(after),
            diff=diff,
        ),
    )
