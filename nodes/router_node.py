import logging

from config.constants import (
    TASK_DEFAULT_TIER,
    TaskType,
    Tier,
)
from core.state import TieredFlowState

logger = logging.getLogger(__name__)


_TASK_PATTERNS: list[tuple[TaskType, list[str]]] = [
    (
        TaskType.CLASSIFICATION,
        [
            "classify",
            "categorize",
            "label",
            "is this",
            "what type",
        ],
    ),
    (
        TaskType.EXTRACTION,
        [
            "extract",
            "pull out",
            "find all",
            "list all",
            "get the",
        ],
    ),
    (
        TaskType.SUMMARIZATION,
        [
            "summarize",
            "summary",
            "tldr",
            "brief",
            "shorten",
        ],
    ),
    (
        TaskType.CODE_GENERATION,
        [
            "write code",
            "implement",
            "function",
            "class",
            "script",
            "debug",
        ],
    ),
    (
        TaskType.REASONING,
        [
            "why",
            "explain",
            "analyze",
            "compare",
            "evaluate",
            "reason",
        ],
    ),
    (
        TaskType.CREATIVE,
        [
            "write a story",
            "poem",
            "creative",
            "imagine",
            "generate",
        ],
    ),
    (
        TaskType.QA,
        [
            "what is",
            "who is",
            "when did",
            "how do",
            "define",
        ],
    ),
]


def task_classifier_node(
    state: TieredFlowState,
) -> TieredFlowState:
    query_lower = state["user_query"].lower()
    detected = TaskType.UNKNOWN

    for task_type, keywords in _TASK_PATTERNS:
        if any(kw in query_lower for kw in keywords):
            detected = task_type
            break

    logger.info(f"[Classifier] Detected: {detected}")
    return {**state, "task_type": detected}


def router_node(state: TieredFlowState) -> TieredFlowState:
    task_type = state.get("task_type", TaskType.UNKNOWN)
    budget = state["budget_remaining_usd"]

    candidate_tier = TASK_DEFAULT_TIER.get(task_type, Tier.MID)
    reason = f"Default for task type '{task_type}'"

    if budget < 0.05:
        candidate_tier = Tier.ULTRA_CHEAP
        reason = f"Budget critically low (${budget:.4f}) → forced ULTRA_CHEAP"
        logger.warning(f"[Router] {reason}")
    elif budget < 0.20 and candidate_tier == Tier.POWER:
        candidate_tier = Tier.QUALITY
        reason = f"Budget low (${budget:.4f}) → downgraded POWER → QUALITY"
        logger.info(f"[Router] {reason}")

    logger.info(f"[Router] Selected: {candidate_tier} | Reason: {reason}")

    return {
        **state,
        "selected_tier": candidate_tier,
        "routing_reason": reason,
    }


def route_after_router(state: TieredFlowState) -> str:
    if state.get("human_override_requested"):
        return "human_tier_override"
    return "llm_call"
