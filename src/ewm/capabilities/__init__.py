"""Optional capability substrates layered above the deterministic EWM core."""

from .cognition import (
    ActionSchema,
    CognitiveActionError,
    CognitiveAgent,
    CognitiveDecision,
    CognitiveTool,
    DecisionProvenance,
    FunctionalCognitiveTool,
    LanguageModelBackend,
    MemoryEntry,
    ModelRequest,
    ModelResponse,
)
from .evolution import (
    EVOLUTION_SCHEMA_VERSION,
    CapabilityKind,
    CapabilityManifest,
    EvolutionProposal,
    EvolutionRegistry,
    GateEvidence,
    PromotionPolicy,
    PromotionReport,
    RollbackReport,
)

__all__ = [
    "EVOLUTION_SCHEMA_VERSION",
    "ActionSchema",
    "CapabilityKind",
    "CapabilityManifest",
    "CognitiveActionError",
    "CognitiveAgent",
    "CognitiveDecision",
    "CognitiveTool",
    "DecisionProvenance",
    "EvolutionProposal",
    "EvolutionRegistry",
    "FunctionalCognitiveTool",
    "GateEvidence",
    "LanguageModelBackend",
    "MemoryEntry",
    "ModelRequest",
    "ModelResponse",
    "PromotionPolicy",
    "PromotionReport",
    "RollbackReport",
]
