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
        TaskType.REALTIME_QA,
        [
            "current",
            "latest",
            "today",
            "news",
            "right now",
            "recently",
            "this week",
            "price of",
            "weather in",
        ],
    ),
    (
        TaskType.WEATHER,
        ["weather", "temperature", "forecast", "raining", "humidity", "wind"],
    ),
    (
        TaskType.DATETIME,
        [
            "what time",
            "what day",
            "today's date",
            "current time",
            "timezone",
            "what year",
            "day is it",
        ],
    ),
    (
        TaskType.CALCULATOR,
        [
            "calculate",
            "compute",
            "how much is",
            "what is the result",
            "convert",
            "how many",
            "percentage",
            "multiply",
            "divide",
            "add",
            "subtract",
        ],
    ),
    (
        TaskType.WIKIPEDIA,
        ["who is", "who was", "history of", "tell me about", "biography", "what was"],
    ),
    (
        TaskType.CLASSIFICATION,
        ["classify", "categorize", "label", "is this", "what type"],
    ),
    (TaskType.EXTRACTION, ["extract", "pull out", "find all", "list all", "get the"]),
    (TaskType.SUMMARIZATION, ["summarize", "summary", "tldr", "brief", "shorten"]),
    (
        TaskType.CODE_GENERATION,
        ["write code", "implement", "function", "class", "script", "debug"],
    ),
    (
        TaskType.REASONING,
        ["why", "explain", "analyze", "compare", "evaluate", "reason"],
    ),
    (TaskType.CREATIVE, ["write a story", "poem", "creative", "imagine", "generate"]),
    (TaskType.QA, ["what is", "who is", "when did", "how do", "define"]),
]


def task_classifier_node(state: TieredFlowState) -> TieredFlowState:
    query = state["user_query"]

    CLASSIFY_PROMPT = f"""Classify the following user query into exactly one of these categories:

        REALTIME_QA     - current events, latest news, live prices, recent happenings
        WEATHER         - weather, temperature, forecast, humidity
        DATETIME        - current time, date, timezone
        CALCULATOR      - math calculations, unit conversions, numerical computations
        WIKIPEDIA       - well-known encyclopedic facts about famous people, places, concepts (must have a clear Wikipedia article)
        SUMMARIZATION   - summarize or shorten a given text
        CODE_GENERATION - write, debug, or explain code
        REASONING       - explain concepts, analyze, compare, evaluate ideas
        CREATIVE        - stories, poems, creative writing
        QA              - general factual questions, historical facts, definitions
        UNKNOWN         - anything that doesn't fit above

        User query: "{query}"

        Rules:
        - WIKIPEDIA only if the query names a specific famous person, place, or concept with a dedicated Wikipedia page (e.g. "Albert Einstein", "Eiffel Tower")
        - "Who is the father of X", "Who founded X", "Who invented X" → use QA, not WIKIPEDIA
        - Use QA for historical facts, attributions, biographical questions
        - Return ONLY the category name, nothing else"""

    task_type = None

    # ── LLM classification ────────────────────────────────────────────────────
    try:
        from providers.groq_provider import GroqProvider

        classifier = GroqProvider(model_id="llama-3.1-8b-instant")
        response = classifier.call(
            prompt=CLASSIFY_PROMPT,
            system="You are a query classifier. Return only the category name, nothing else.",
            max_tokens=10,
        )
        raw = response.content.strip().upper()
        logger.info(f"[Classifier] LLM classified '{query}' as: {raw}")

        # Match to TaskType
        type_map = {
            "REALTIME_QA": TaskType.REALTIME_QA,
            "WEATHER": TaskType.WEATHER,
            "DATETIME": TaskType.DATETIME,
            "CALCULATOR": TaskType.CALCULATOR,
            "WIKIPEDIA": TaskType.WIKIPEDIA,
            "SUMMARIZATION": TaskType.SUMMARIZATION,
            "CODE_GENERATION": TaskType.CODE_GENERATION,
            "REASONING": TaskType.REASONING,
            "CREATIVE": TaskType.CREATIVE,
            "QA": TaskType.QA,
            "UNKNOWN": TaskType.UNKNOWN,
        }
        task_type = type_map.get(raw)

    except Exception as e:
        logger.warning(
            f"[Classifier] LLM classification failed: {e}. Falling back to keywords."
        )

    # ── Keyword fallback ──────────────────────────────────────────────────────
    if task_type is None:
        query_lower = query.lower()
        for pattern_type, keywords in _TASK_PATTERNS:
            if any(kw in query_lower for kw in keywords):
                task_type = pattern_type
                logger.info(f"[Classifier] Keyword fallback classified as: {task_type}")
                break

    if task_type is None:
        task_type = TaskType.UNKNOWN
        logger.info("[Classifier] Defaulting to UNKNOWN")

    return {**state, "task_type": task_type}


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
