import logging
from datetime import datetime, timezone

from cache.semantic_cache import get_cache
from config.constants import MODELS
from core.state import TieredFlowState
from providers import get_provider

logger = logging.getLogger(__name__)


def llm_call_node(
    state: TieredFlowState,
) -> TieredFlowState:
    tier = state["selected_tier"]
    meta = MODELS[tier]
    provider = get_provider(tier)

    logger.info(f"[LLM] Calling {meta.model_id} (tier={tier})")

    try:
        response = provider.call(
            prompt=state["user_query"],
            system="You are a helpful, concise assistant.",
            max_tokens=1024,
        )
    except Exception as e:
        logger.error(f"[LLM] Call failed: {e}. Falling back to POWER tier.")
        from config.constants import Tier

        provider = get_provider(Tier.POWER)
        response = provider.call(
            prompt=state["user_query"],
            system="You are a helpful, concise assistant.",
            max_tokens=1024,
        )
        tier = Tier.POWER
        meta = MODELS[tier]

    cost_usd = (response.input_tokens / 1000) * meta.cost_per_1k_input + (
        response.output_tokens / 1000
    ) * meta.cost_per_1k_output

    new_total_calls = state["total_calls"] + 1

    log_entry = {
        "call_number": new_total_calls,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query_snippet": state["user_query"][:80],
        "task_type": state.get("task_type"),
        "tier": tier,
        "model_id": response.model_id,
        "provider": response.provider,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cost_usd": round(cost_usd, 6),
        "latency_ms": response.latency_ms,
        "served_from_cache": False,
    }

    logger.info(
        f"[LLM] Done. tokens=({response.input_tokens}in/{response.output_tokens}out) "
        f"cost=${cost_usd:.6f} latency={response.latency_ms}ms"
    )

    cache = get_cache()
    cache.store(
        query=state["user_query"],
        response=response.content,
        tier_used=tier,
        cost_usd=cost_usd,
    )

    return {
        **state,
        "llm_response": response.content,
        "tokens_used_input": response.input_tokens,
        "tokens_used_output": response.output_tokens,
        "cost_usd": round(cost_usd, 6),
        "latency_ms": response.latency_ms,
        "budget_remaining_usd": max(state["budget_remaining_usd"] - cost_usd, 0.0),
        "total_cost_usd": round(state["total_cost_usd"] + cost_usd, 6),
        "total_calls": new_total_calls,
        "call_log": state["call_log"] + [log_entry],
        "final_response": response.content,
        "served_from_cache": False,
    }
