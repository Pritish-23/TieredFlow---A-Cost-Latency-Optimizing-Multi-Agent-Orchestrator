from typing import Literal, Optional, TypedDict

from config.constants import TaskType, Tier


class TieredFlowState(TypedDict):

    # Input
    user_query: str
    session_id: str
    original_query: Optional[str]
    rewritten_query: Optional[str]

    # Guardrail
    guardrail_passed: Optional[bool]
    guardrail_reason: Optional[str]

    # Task classification
    task_type: Optional[TaskType]

    # Routing
    selected_tier: Optional[Tier]
    routing_reason: Optional[str]
    budget_remaining_usd: float

    # Semantic cache
    cache_match_found: Optional[bool]
    cache_similarity_score: Optional[float]
    cache_matched_query_id: Optional[str]
    cache_user_decision: Optional[Literal["accept", "reject", "pending"]]
    cached_response: Optional[str]

    # LLM call
    llm_response: Optional[str]
    tokens_used_input: Optional[int]
    tokens_used_output: Optional[int]
    cost_usd: Optional[float]
    latency_ms: Optional[int]
    system_prompt: Optional[str]
    confidence_score: Optional[int]

    # Human override
    human_override_requested: bool
    human_override_tier: Optional[Tier]

    # Output
    final_response: Optional[str]
    served_from_cache: bool

    # Session totals
    total_cost_usd: float
    total_calls: int
    call_log: list[dict]

    # Query
    query_mode: Optional[str]
    rewrite_pending_decision: Optional[bool]

    # Conversation History
    conversation_history: Optional[
        list
    ]  # ← add this: list of {"role": ..., "content": ...}


def initial_state(
    user_query: str,
    session_id: str,
    budget: float,
    query_mode: str = "auto",
    conversation_history: list = None,
) -> TieredFlowState:
    return TieredFlowState(
        user_query=user_query,
        session_id=session_id,
        original_query=user_query,
        rewritten_query=None,
        guardrail_passed=None,
        guardrail_reason=None,
        task_type=None,
        selected_tier=None,
        routing_reason=None,
        budget_remaining_usd=budget,
        cache_match_found=None,
        cache_similarity_score=None,
        cache_matched_query_id=None,
        cache_user_decision=None,
        cached_response=None,
        llm_response=None,
        tokens_used_input=None,
        tokens_used_output=None,
        cost_usd=None,
        latency_ms=None,
        human_override_requested=False,
        human_override_tier=None,
        final_response=None,
        served_from_cache=False,
        total_cost_usd=0.0,
        total_calls=0,
        call_log=[],
        system_prompt=None,
        confidence_score=None,
        query_mode=query_mode,
        rewrite_pending_decision=None,
        conversation_history=conversation_history or [],
    )
