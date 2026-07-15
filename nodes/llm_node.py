import logging
from datetime import datetime, timezone

from cache.semantic_cache import get_cache
from config.constants import MODELS
from core.state import TieredFlowState
from providers import get_provider

logger = logging.getLogger(__name__)


def llm_call_node(state: TieredFlowState) -> TieredFlowState:
    tier = state["selected_tier"]
    meta = MODELS[tier]
    provider = get_provider(tier)

    logger.info(f"[LLM] Calling {meta.model_id} (tier={tier})")

    from config.constants import TaskType
    from tools.calculator_tool import get_calculator_tool
    from tools.datetime_tool import get_datetime_tool
    from tools.search_tool import get_search_tool
    from tools.weather_tool import get_weather_tool
    from tools.wiki_tool import get_wiki_tool

    prompt = state["user_query"]
    system = "You are a helpful, concise assistant."
    task_type = state.get("task_type")

    # ── Tool dispatcher ───────────────────────────────────────────────────────
    if task_type == TaskType.REALTIME_QA:
        logger.info("[LLM] Tool: WebSearch")
        results = get_search_tool().search(prompt)
        system = (
            "You are a helpful assistant with access to live web search results. "
            "Answer using the search results below.\n\n"
            f"Search Results:\n{results}"
        )

    elif task_type == TaskType.WIKIPEDIA:
        logger.info("[LLM] Tool: Wikipedia")
        wiki = get_wiki_tool()
        results = wiki.search(prompt)
        system = (
            "You are a helpful assistant with access to Wikipedia. "
            "Answer using the Wikipedia content below.\n\n"
            f"Wikipedia Content:\n{results}"
        )

    elif task_type == TaskType.CALCULATOR:
        logger.info("[LLM] Tool: Calculator")
        calc = get_calculator_tool()
        results = calc.calculate(prompt)
        system = (
            "You are a helpful assistant with a calculator. "
            "Use the calculation result below to answer the user.\n\n"
            f"Calculation Result:\n{results}"
        )

    elif task_type == TaskType.DATETIME:
        logger.info("[LLM] Tool: DateTime")
        dt_tool = get_datetime_tool()
        tz_str = dt_tool.extract_timezone(prompt)
        results = dt_tool.get_current_datetime(tz_str)
        system = (
            "You are a helpful assistant with access to current date and time. "
            "Answer using the datetime information below.\n\n"
            f"DateTime Info:\n{results}"
        )

    elif task_type == TaskType.WEATHER:
        logger.info("[LLM] Tool: Weather")
        weather = get_weather_tool()
        location = weather.extract_location(prompt)
        results = weather.get_weather(location)
        system = (
            "You are a helpful assistant with access to live weather data. "
            "Answer using the weather information below.\n\n"
            f"Weather Data:\n{results}"
        )

    # ── LLM call ──────────────────────────────────────────────────────────────
    try:
        response = provider.call(
            prompt=prompt,
            system=system,
            max_tokens=1024,
        )
    except Exception as e:
        logger.error(f"[LLM] Call failed: {e}. Falling back to POWER tier.")
        from config.constants import Tier

        provider = get_provider(Tier.POWER)
        response = provider.call(
            prompt=prompt,
            system=system,
            max_tokens=1024,
        )
        tier = Tier.POWER
        meta = MODELS[tier]

    cost_usd = (response.input_tokens / 1000) * meta.cost_per_1k_input + (
        response.output_tokens / 1000
    ) * meta.cost_per_1k_output

    new_total_calls = state["total_calls"] + 1

    # ── Confidence scoring ─────────────────────────────────────────────────────
    confidence_score = None
    try:
        from providers.groq_provider import GroqProvider
        scorer = GroqProvider(model_id="llama-3.1-8b-instant")
        score_response = scorer.call(
            prompt=(
                f"Question: {state['user_query']}\n\n"
                f"Answer: {response.content}\n\n"
                "Rate the confidence of this answer on a scale of 1-10. "
                "Return ONLY a single integer between 1 and 10. Nothing else."
            ),
            system="You are a response quality evaluator. Return only a number 1-10.",
            max_tokens=5,
        )
        score_text = score_response.content.strip()
        confidence_score = int("".join(filter(str.isdigit, score_text)) or "0")
        confidence_score = max(1, min(10, confidence_score))
        logger.info(f"[LLM] Confidence score: {confidence_score}/10")
    except Exception as e:
        logger.warning(f"[LLM] Confidence scoring failed: {e}")

    # ── Build log entry ────────────────────────────────────────────────────────
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
        "confidence_score": confidence_score,
    }

    logger.info(
        f"[LLM] Done. tokens=({response.input_tokens}in/{response.output_tokens}out) "
        f"cost=${cost_usd:.6f} latency={response.latency_ms}ms"
    )

    # ── Store in semantic cache ────────────────────────────────────────────────
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
        "system_prompt": system,
        "confidence_score": confidence_score,
        "budget_remaining_usd": max(state["budget_remaining_usd"] - cost_usd, 0.0),
        "total_cost_usd": round(state["total_cost_usd"] + cost_usd, 6),
        "total_calls": new_total_calls,
        "call_log": state["call_log"] + [log_entry],
        "final_response": response.content,
        "served_from_cache": False,
    }
