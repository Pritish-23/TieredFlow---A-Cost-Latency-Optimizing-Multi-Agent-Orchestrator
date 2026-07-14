import logging

from langgraph.types import interrupt

from config.constants import Tier
from core.state import TieredFlowState

logger = logging.getLogger(__name__)


def human_cache_decision_node(
    state: TieredFlowState,
) -> TieredFlowState:
    score = state["cache_similarity_score"]

    logger.info(f"[HITL] Interrupting for cache decision. score={score:.4f}")

    user_input = interrupt(
        {
            "type": "cache_decision",
            "message": (
                f"A similar query was found in cache "
                f"(similarity: {score:.0%}). "
                f"Use the cached response?"
            ),
            "cached_response_preview": (
                state["cached_response"][:300] + "..."
                if state["cached_response"] and len(state["cached_response"]) > 300
                else state["cached_response"]
            ),
            "options": ["accept", "reject"],
        }
    )

    decision = user_input.get("decision", "reject")
    logger.info(f"[HITL] User cache decision: {decision}")

    if decision == "accept":
        return {
            **state,
            "cache_user_decision": "accept",
            "served_from_cache": True,
            "final_response": state["cached_response"],
        }

    return {
        **state,
        "cache_user_decision": "reject",
        "cache_match_found": False,
    }


def route_after_cache_hitl(state: TieredFlowState) -> str:
    if state.get("cache_user_decision") == "accept":
        return "end"
    return "router"


def human_tier_override_node(
    state: TieredFlowState,
) -> TieredFlowState:
    logger.info(
        f"[HITL] Interrupting for tier override. Current: {state['selected_tier']}"
    )

    user_input = interrupt(
        {
            "type": "tier_override",
            "message": (
                f"Router selected tier '{state['selected_tier']}' "
                f"({state['routing_reason']}). Override?"
            ),
            "current_tier": state["selected_tier"],
            "available_tiers": [t.value for t in Tier],
            "budget_remaining_usd": state["budget_remaining_usd"],
        }
    )

    chosen_tier = user_input.get("tier", state["selected_tier"])
    logger.info(f"[HITL] User selected: {chosen_tier}")

    return {
        **state,
        "selected_tier": Tier(chosen_tier),
        "human_override_tier": Tier(chosen_tier),
        "routing_reason": f"Human override → {chosen_tier}",
    }
