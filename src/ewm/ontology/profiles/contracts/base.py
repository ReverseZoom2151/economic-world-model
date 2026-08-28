"""Versioned scenario-adapter boundary for ontology projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ewm.core.domain.records import freeze_value
from ewm.core.provenance.serialization import content_digest

from ...graph.identity import make_ontology_ref
from ...graph.model import (
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


def artifact_source(
    context: OntologyProfileContext,
    filename: str,
    *,
    selector: str | None = None,
) -> SourceLocator:
    """Locate one exact record inside the already-verified source bundle."""

    try:
        digest = str(context.payload_digests[filename])
    except KeyError as error:
        raise ValueError(f"profile requested absent payload {filename!r}") from error
    return SourceLocator(
        source_kind="verified_run",
        source_id=context.run_source.source_id,
        artifact_path=f"run/{filename}",
        record_selector=selector,
        payload_digest=digest,
    )


class ProfileBuilder:
    """Small deterministic builder that keeps profile assertions sourced and immutable."""

    def __init__(
        self,
        context: OntologyProfileContext,
        *,
        profile_identity: str,
        source_digest: str,
    ) -> None:
        self.context = context
        self.profile_identity = profile_identity
        self.source_digest = source_digest
        self.objects: list[OntologyObject] = []
        self.relations: list[RelationAssertion] = []
        self.measurements: list[Measurement] = []
        self.coverage: list[CoverageEntry] = []

    def declaration(
        self,
        kind: str,
        semantic_keys: Any,
        properties: Mapping[str, Any],
    ) -> OntologyRef:
        """Add one adapter-derived economic declaration."""

        ref = make_ontology_ref(
            namespace="declaration",
            kind=kind,
            source_identity=self.source_digest,
            semantic_keys=semantic_keys,
        )
        self.objects.append(
            OntologyObject(
                ref=ref,
                layer="economic_declaration",
                properties={
                    **properties,
                    "evidence_origin": "adapter_derived",
                    "profile_identity": self.profile_identity,
                },
                sources=(self.context.adapter_source,),
            )
        )
        return ref

    def object(
        self,
        kind: str,
        layer: str,
        semantic_keys: Any,
        properties: Mapping[str, Any],
        *,
        sources: tuple[SourceLocator, ...],
    ) -> OntologyRef:
        """Add one run-derived object with an exact semantic identity."""

        ref = make_ontology_ref(
            namespace="profile",
            kind=kind,
            source_identity=self.context.run_source.source_id,
            semantic_keys={"profile": self.profile_identity, "record": semantic_keys},
        )
        self.objects.append(
            OntologyObject(
                ref=ref,
                layer=layer,
                properties=properties,
                sources=sources,
            )
        )
        return ref

    def relation(
        self,
        relation_type: str,
        source: OntologyRef,
        target: OntologyRef,
        semantic_keys: Any,
        *,
        locator: SourceLocator,
        properties: Mapping[str, Any] | None = None,
    ) -> OntologyRef:
        """Add one exactly sourced directed relation."""

        ref = make_ontology_ref(
            namespace="profile-relation",
            kind="relation_assertion",
            source_identity=self.context.run_source.source_id,
            semantic_keys={
                "profile": self.profile_identity,
                "relation_type": relation_type,
                "source": source.id,
                "target": target.id,
                "record": semantic_keys,
            },
        )
        self.relations.append(
            RelationAssertion(
                ref=ref,
                relation_type=relation_type,
                source=source,
                target=target,
                properties={} if properties is None else properties,
                sources=(locator,),
            )
        )
        return ref

    def measurement(
        self,
        subject: OntologyRef,
        name: str,
        value: Any,
        *,
        unit: str,
        status: str,
        sample: Mapping[str, Any],
        uncertainty: Mapping[str, Any],
        locator: SourceLocator,
        semantic_keys: Any | None = None,
    ) -> OntologyRef:
        """Add one profile-specific sourced measurement."""

        ref = make_ontology_ref(
            namespace="profile-measurement",
            kind="measurement",
            source_identity=self.context.run_source.source_id,
            semantic_keys={
                "profile": self.profile_identity,
                "subject": subject.id,
                "name": name,
                "record": semantic_keys,
            },
        )
        self.measurements.append(
            Measurement(
                ref=ref,
                subject=subject,
                name=name,
                value=value,
                unit=unit,
                status=status,
                sample=sample,
                uncertainty=uncertainty,
                sources=(locator,),
            )
        )
        return ref

    def gap(
        self,
        field: str,
        status: str,
        reason: str,
        *,
        source: SourceLocator | None = None,
    ) -> None:
        """Record one explicit unavailable, omitted, or rejected semantic field."""

        self.coverage.append(
            CoverageEntry(
                source=self.context.adapter_source if source is None else source,
                field=field,
                status=status,
                targets=(),
                reason=reason,
            )
        )

    def projected(
        self,
        field: str,
        *targets: OntologyRef,
        source: SourceLocator,
    ) -> None:
        """Record one profile-specific projected semantic field."""

        self.coverage.append(
            CoverageEntry(
                source=source,
                field=field,
                status="projected",
                targets=tuple(targets),
                reason=None,
            )
        )

    def add_profile_provenance(self) -> OntologyRef:
        """Materialize the selected profile and its source digest as provenance."""

        return self.object(
            "source_locator",
            "provenance",
            {"profile_identity": self.profile_identity},
            {
                "profile_identity": self.profile_identity,
                "source_digest": self.source_digest,
                "compatibility": {
                    "artifact_schema": self.context.artifact_schema,
                    "experiment": self.context.experiment,
                    "package_version": self.context.package_version,
                },
            },
            sources=(self.context.adapter_source,),
        )

    def finish(self) -> ProfileProjection:
        """Freeze the accumulated projection fragment."""

        return ProfileProjection(
            objects=tuple(self.objects),
            relations=tuple(self.relations),
            measurements=tuple(self.measurements),
            coverage=tuple(self.coverage),
        )
