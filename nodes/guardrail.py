import logging
import re

from config.constants import GUARDRAIL_BLOCKED_PATTERNS
from core.state import TieredFlowState

logger = logging.getLogger(__name__)


def guardrail_node(
    state: TieredFlowState,
) -> TieredFlowState:
    query = state["user_query"].lower()

    for pattern in GUARDRAIL_BLOCKED_PATTERNS:
        if re.search(re.escape(pattern), query):
            logger.warning(f"[Guardrail] Blocked. Pattern matched: '{pattern}'")
            return {
                **state,
                "guardrail_passed": False,
                "guardrail_reason": f"Matched blocked pattern: '{pattern}'",
                "final_response": (
                    "⚠️ This query was flagged by the safety guardrail "
                    "and cannot be processed."
                ),
            }

    if len(state["user_query"].strip()) < 3:
        return {
            **state,
            "guardrail_passed": False,
            "guardrail_reason": "Query too short.",
            "final_response": "Please provide a more detailed query.",
        }

    logger.info("[Guardrail] Query passed.")
    return {**state, "guardrail_passed": True}


def route_after_guardrail(state: TieredFlowState) -> str:
    if state.get("guardrail_passed"):
        return "cache_lookup"
    return "end"
