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

__all__ = [
    "ActionSchema",
    "CognitiveActionError",
    "CognitiveAgent",
    "CognitiveDecision",
    "CognitiveTool",
    "DecisionProvenance",
    "FunctionalCognitiveTool",
    "LanguageModelBackend",
    "MemoryEntry",
    "ModelRequest",
    "ModelResponse",
]
