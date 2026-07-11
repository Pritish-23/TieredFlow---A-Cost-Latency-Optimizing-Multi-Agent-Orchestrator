import logging

from cache.semantic_cache import get_cache
from config.settings import settings
from core.state import TieredFlowState

logger = logging.getLogger(__name__)


def cache_lookup_node(
    state: TieredFlowState,
) -> TieredFlowState:
    cache = get_cache()
    result = cache.lookup(state["user_query"])

    if not result.found:
        logger.info("[Cache] No match. Proceeding to router.")
        return {
            **state,
            "cache_match_found": False,
            "cache_similarity_score": result.similarity_score,
        }

    logger.info(f"[Cache] Match found. score={result.similarity_score:.4f}")

    return {
        **state,
        "cache_match_found": True,
        "cache_similarity_score": result.similarity_score,
        "cache_matched_query_id": result.matched_query_id,
        "cached_response": result.cached_response,
        "cache_user_decision": "pending",
    }


def route_after_cache(state: TieredFlowState) -> str:
    if not state.get("cache_match_found"):
        return "task_classifier"

    score = state["cache_similarity_score"]

    if score >= settings.cache_similarity_high:
        logger.info(f"[Cache] Auto-serving (score={score:.4f}).")
        return "auto_serve_cache"

    logger.info(f"[Cache] HITL required (score={score:.4f}).")
    return "human_cache_decision"


def auto_serve_cache_node(
    state: TieredFlowState,
) -> TieredFlowState:
    logger.info("[Cache] Auto-serving cached response.")
    return {
        **state,
        "cache_user_decision": "accept",
        "served_from_cache": True,
        "final_response": state["cached_response"],
    }
