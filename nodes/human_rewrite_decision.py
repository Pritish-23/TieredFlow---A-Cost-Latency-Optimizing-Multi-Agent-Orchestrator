import logging

from langgraph.types import interrupt

from core.state import TieredFlowState

logger = logging.getLogger(__name__)


def human_rewrite_decision_node(state: TieredFlowState) -> TieredFlowState:
    """
    Pauses graph execution so the UI can ask the user:
    'Use original query or rewritten query?'
    Resumes with state['rewrite_choice'] set to 'original' or 'rewritten'.
    """
    decision = interrupt(
        {
            "original_query": state["original_query"],
            "rewritten_query": state["rewritten_query"],
        }
    )

    choice = decision.get("choice", "rewritten")  # default to rewritten if unclear
    logger.info(f"[RewriteDecision] User chose: {choice}")

    final_query = (
        state["original_query"] if choice == "original" else state["rewritten_query"]
    )

    return {
        **state,
        "user_query": final_query,
        "rewrite_pending_decision": False,
    }


def route_after_rewrite(state: TieredFlowState) -> str:
    if state.get("rewrite_pending_decision"):
        return "human_rewrite_decision"
    return "router"
