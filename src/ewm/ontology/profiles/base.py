"""Versioned scenario-adapter boundary for ontology projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ewm.core.records import freeze_value
from ewm.core.serialization import content_digest

from ..model import (
    CoverageEntry,
    Measurement,
    OntologyObject,
    OntologyRef,
    RelationAssertion,
    SourceLocator,
)


@dataclass(frozen=True, slots=True)
class ProfileProjection:
    """Additional ontology records emitted by one compatible scenario profile."""

    objects: tuple[OntologyObject, ...] = ()
    relations: tuple[RelationAssertion, ...] = ()
    measurements: tuple[Measurement, ...] = ()
    coverage: tuple[CoverageEntry, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "objects", tuple(self.objects))
        object.__setattr__(self, "relations", tuple(self.relations))
        object.__setattr__(self, "measurements", tuple(self.measurements))
        object.__setattr__(self, "coverage", tuple(self.coverage))


@dataclass(frozen=True, slots=True)
class OntologyProfileContext:
    """Verified, bounded, immutable source data made available to an adapter."""

    artifact_schema: str
    experiment: str
    package_version: str
    scenario: str
    preset: str
    seed: int
    run_ref: OntologyRef
    manifest: Mapping[str, Any]
    config: Mapping[str, Any]
    metrics: Mapping[str, Any]
    events: tuple[Mapping[str, Any], ...]
    traces: Mapping[str, Any]
    payload_digests: Mapping[str, str]
    run_source: SourceLocator
    adapter_source: SourceLocator

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest", freeze_value(self.manifest))
        object.__setattr__(self, "config", freeze_value(self.config))
        object.__setattr__(self, "metrics", freeze_value(self.metrics))
        object.__setattr__(
            self,
            "events",
            tuple(freeze_value(event) for event in self.events),
        )
        object.__setattr__(self, "traces", freeze_value(self.traces))
        object.__setattr__(self, "payload_digests", freeze_value(self.payload_digests))


class OntologyProfile(Protocol):
    """Structural contract for a versioned, read-only scenario ontology adapter."""

    identity: str
    experiment_ids: frozenset[str]
    package_versions: frozenset[str]
    artifact_schemas: frozenset[str]
    source_digest: str

    def project(self, context: OntologyProfileContext) -> ProfileProjection: ...


def profile_digest(profile: OntologyProfile) -> str:
    """Return the canonical identity digest of a profile's compatibility declaration."""

    return content_digest(
        {
            "identity": profile.identity,
            "experiment_ids": profile.experiment_ids,
            "package_versions": profile.package_versions,
            "artifact_schemas": profile.artifact_schemas,
            "source_digest": profile.source_digest,
        }
    )

