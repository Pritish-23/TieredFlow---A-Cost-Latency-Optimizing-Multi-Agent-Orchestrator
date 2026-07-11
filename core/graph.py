from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from core.state import TieredFlowState
from nodes.cache_node import (
    auto_serve_cache_node,
    cache_lookup_node,
    route_after_cache,
)
from nodes.guardrail import (
    guardrail_node,
    route_after_guardrail,
)
from nodes.human_override import (
    human_cache_decision_node,
    human_tier_override_node,
    route_after_cache_hitl,
)
from nodes.llm_node import llm_call_node
from nodes.router_node import (
    route_after_router,
    router_node,
    task_classifier_node,
)


def build_graph():
    builder = StateGraph(TieredFlowState)

    # Register nodes
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("cache_lookup", cache_lookup_node)
    builder.add_node("auto_serve_cache", auto_serve_cache_node)
    builder.add_node("human_cache_decision", human_cache_decision_node)
    builder.add_node("task_classifier", task_classifier_node)
    builder.add_node("router", router_node)
    builder.add_node("human_tier_override", human_tier_override_node)
    builder.add_node("llm_call", llm_call_node)

    # Entry point
    builder.add_edge(START, "guardrail")

    # Guardrail → conditional
    builder.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"cache_lookup": "cache_lookup", "end": END},
    )

    # Cache lookup → conditional
    builder.add_conditional_edges(
        "cache_lookup",
        route_after_cache,
        {
            "task_classifier": "task_classifier",
            "auto_serve_cache": "auto_serve_cache",
            "human_cache_decision": "human_cache_decision",
        },
    )

    # Auto serve → END
    builder.add_edge("auto_serve_cache", END)

    # HITL cache decision → conditional
    builder.add_conditional_edges(
        "human_cache_decision",
        route_after_cache_hitl,
        {"end": END, "task_classifier": "task_classifier"},
    )

    # Task classifier → router
    builder.add_edge("task_classifier", "router")

    # Router → conditional
    builder.add_conditional_edges(
        "router",
        route_after_router,
        {
            "human_tier_override": "human_tier_override",
            "llm_call": "llm_call",
        },
    )

    # Human tier override → LLM
    builder.add_edge("human_tier_override", "llm_call")

    # LLM → END
    builder.add_edge("llm_call", END)

    # Compile with checkpointer for interrupt/resume support
    checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "human_cache_decision",
            "human_tier_override",
        ],
    )


graph = build_graph()
