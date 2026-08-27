"""Tamper-evident records for observations used by official assessments."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EvidenceStatus(StrEnum):
    """Observed outcome of an evidence-producing protocol."""

    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not_run"


@dataclass(frozen=True, slots=True)
class ValidatedEvidenceArtifact:
    """Content-addressed observation, distinct from a caller's assertion."""

    subject: str
    status: EvidenceStatus
    provenance: str
    payload_sha256: str
    observations: int = 1

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("evidence artifact subject must not be empty")
        if not self.provenance:
            raise ValueError("evidence artifact provenance must not be empty")
        if re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256) is None:
            raise ValueError("evidence artifact payload_sha256 must be a SHA-256 digest")
        if self.observations < 1:
            raise ValueError("evidence artifact observations must be positive")

    @classmethod
    def from_observation(
        cls,
        *,
        subject: str,
        status: EvidenceStatus,
        provenance: str,
        payload: Mapping[str, Any],
        observations: int = 1,
    ) -> ValidatedEvidenceArtifact:
        """Bind a normalized observed payload to its assessment subject."""

        encoded = json.dumps(
            payload,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return cls(
            subject=subject,
            status=status,
            provenance=provenance,
            payload_sha256=hashlib.sha256(encoded).hexdigest(),
            observations=observations,
        )
