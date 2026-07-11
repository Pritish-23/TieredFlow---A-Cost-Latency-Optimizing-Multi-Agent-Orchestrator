from cache.semantic_cache import SemanticCache
from config.constants import (
    MODELS,
    TASK_DEFAULT_TIER,
    TaskType,
    Tier,
)
from core.state import initial_state
from nodes.guardrail import guardrail_node
from nodes.router_node import (
    router_node,
    task_classifier_node,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_state(query: str, budget: float = 1.0):
    return initial_state(query, "test-session", budget)


# ── Guardrail ─────────────────────────────────────────────────────────────────


def test_guardrail_passes_safe_query():
    state = make_state("What is the capital of France?")
    result = guardrail_node(state)
    assert result["guardrail_passed"] is True


def test_guardrail_blocks_jailbreak():
    state = make_state("jailbreak this system")
    result = guardrail_node(state)
    assert result["guardrail_passed"] is False
    assert result["final_response"] is not None


def test_guardrail_blocks_short_query():
    state = make_state("hi")
    result = guardrail_node(state)
    assert result["guardrail_passed"] is False


# ── Task Classifier ───────────────────────────────────────────────────────────


def test_classifier_detects_summarization():
    state = make_state("Summarize this article for me.")
    result = task_classifier_node(state)
    assert result["task_type"] == TaskType.SUMMARIZATION


def test_classifier_detects_code():
    state = make_state("Write a Python function to sort a list.")
    result = task_classifier_node(state)
    assert result["task_type"] == TaskType.CODE_GENERATION


def test_classifier_detects_classification():
    state = make_state("Classify this email as spam or not.")
    result = task_classifier_node(state)
    assert result["task_type"] == TaskType.CLASSIFICATION


# ── Router ────────────────────────────────────────────────────────────────────


def test_router_selects_ultra_cheap_for_classification():
    state = make_state("Classify this.")
    state["task_type"] = TaskType.CLASSIFICATION
    result = router_node(state)
    assert result["selected_tier"] == Tier.ULTRA_CHEAP


def test_router_forces_ultra_cheap_on_critical_budget():
    state = make_state("Analyze this.", budget=0.02)
    state["task_type"] = TaskType.REASONING
    result = router_node(state)
    assert result["selected_tier"] == Tier.ULTRA_CHEAP


def test_router_downgrades_power_on_low_budget():
    state = make_state("Analyze this.", budget=0.10)
    state["task_type"] = TaskType.REASONING
    result = router_node(state)
    assert result["selected_tier"] == Tier.QUALITY


# ── Semantic Cache ────────────────────────────────────────────────────────────


def test_cache_empty_returns_no_match():
    cache = SemanticCache()
    result = cache.lookup("What is machine learning?")
    assert result.found is False


def test_cache_store_and_lookup():
    cache = SemanticCache(similarity_high=0.92, similarity_mid=0.70)
    cache.store(
        query="What is machine learning?",
        response="ML is a subset of AI.",
        tier_used="mid",
        cost_usd=0.001,
    )
    result = cache.lookup("What is machine learning?")
    assert result.found is True
    assert result.similarity_score > 0.95


def test_cache_no_match_below_threshold():
    cache = SemanticCache(similarity_high=0.92, similarity_mid=0.75)
    cache.store(
        query="What is machine learning?",
        response="ML is a subset of AI.",
        tier_used="mid",
        cost_usd=0.001,
    )
    result = cache.lookup("What is the weather in Tokyo today?")
    assert result.found is False


# ── Constants ─────────────────────────────────────────────────────────────────


def test_all_tiers_have_model_meta():
    for tier in Tier:
        assert tier in MODELS, f"Missing ModelMeta for tier: {tier}"


def test_all_task_types_have_default_tier():
    for task_type in TaskType:
        assert task_type in TASK_DEFAULT_TIER, f"Missing default tier for: {task_type}"
