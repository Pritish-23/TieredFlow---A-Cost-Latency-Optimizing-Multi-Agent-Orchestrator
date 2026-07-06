from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    ULTRA_CHEAP = "ultra_cheap"
    MID = "mid"
    QUALITY = "quality"
    POWER = "power"


@dataclass(frozen=True)
class ModelMeta:
    model_id: str
    provider: str
    tier: Tier
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: int
    context_window: int


MODELS: dict[Tier, ModelMeta] = {
    Tier.ULTRA_CHEAP: ModelMeta(
        model_id="llama-3.1-8b-instant",
        provider="groq",
        tier=Tier.ULTRA_CHEAP,
        cost_per_1k_input=0.00005,
        cost_per_1k_output=0.00008,
        avg_latency_ms=300,
        context_window=128_000,
    ),
    Tier.MID: ModelMeta(
        model_id="claude-haiku-4-5-20251001",
        provider="anthropic",
        tier=Tier.MID,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        avg_latency_ms=700,
        context_window=200_000,
    ),
    Tier.QUALITY: ModelMeta(
        model_id="gpt-4o-mini",
        provider="openai",
        tier=Tier.QUALITY,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.00060,
        avg_latency_ms=1_200,
        context_window=128_000,
    ),
    Tier.POWER: ModelMeta(
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        tier=Tier.POWER,
        cost_per_1k_input=0.00300,
        cost_per_1k_output=0.01500,
        avg_latency_ms=2_500,
        context_window=200_000,
    ),
}


class TaskType(str, Enum):
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    CREATIVE = "creative"
    QA = "qa"
    UNKNOWN = "unknown"


TASK_DEFAULT_TIER: dict[TaskType, Tier] = {
    TaskType.CLASSIFICATION: Tier.ULTRA_CHEAP,
    TaskType.EXTRACTION: Tier.ULTRA_CHEAP,
    TaskType.SUMMARIZATION: Tier.MID,
    TaskType.QA: Tier.MID,
    TaskType.CREATIVE: Tier.QUALITY,
    TaskType.CODE_GENERATION: Tier.QUALITY,
    TaskType.REASONING: Tier.POWER,
    TaskType.UNKNOWN: Tier.MID,
}


GUARDRAIL_BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "jailbreak",
    "dan mode",
    "act as if you have no restrictions",
]
