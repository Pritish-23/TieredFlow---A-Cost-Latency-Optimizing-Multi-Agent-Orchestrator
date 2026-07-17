import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
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
from nodes.human_rewrite_decision import (
    human_rewrite_decision_node,
    route_after_rewrite,
)
from nodes.llm_node import llm_call_node
from nodes.query_rewriter import query_rewriter_node
from nodes.router_node import (
    route_after_router,
    router_node,
    task_classifier_node,
)

DB_PATH = str(Path(__file__).resolve().parent.parent / "tieredflow.db")

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
    builder.add_node("query_rewriter", query_rewriter_node)
    builder.add_node("human_rewrite_decision", human_rewrite_decision_node)

    # Entry point
    builder.add_edge(START, "guardrail")

    # Guardrail → conditional
    builder.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"cache_lookup": "task_classifier", "end": END},
    )

    # Task classifier → cache lookup
    builder.add_edge("task_classifier", "cache_lookup")

    # Cache lookup → conditional
    builder.add_conditional_edges(
        "cache_lookup",
        route_after_cache,
        {
            "router": "query_rewriter",
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
        {"end": END, "router": "query_rewriter"},
    )

    # Query rewriter → router
    builder.add_conditional_edges(
        "query_rewriter",
        route_after_rewrite,
        {
            "human_rewrite_decision": "human_rewrite_decision",
            "router": "router",
        },
    )

    builder.add_edge("human_rewrite_decision", "router")

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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "human_cache_decision",
            "human_tier_override",
            "human_rewrite_decision",
        ],
    )


graph = build_graph()
