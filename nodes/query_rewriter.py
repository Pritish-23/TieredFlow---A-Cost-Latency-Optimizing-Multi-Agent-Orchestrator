import logging

from core.state import TieredFlowState
from providers.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """You are a query optimization assistant.
Your job is to rewrite vague or ambiguous user queries into clear, specific, and detailed queries.

Rules:
- Keep the original intent intact
- Make the query more specific and actionable
- Fix grammar and spelling errors
- If the query is already clear and specific, return it as is
- Return ONLY the rewritten query, nothing else
- No explanations, no preamble, no quotes"""


def query_rewriter_node(state: TieredFlowState) -> TieredFlowState:
    original = state["user_query"]
    mode = state.get("query_mode", "auto")

    logger.info(f"[Rewriter] Mode: {mode} | Original query: {original}")

    # ── Mode: original — skip rewriting entirely ───────────────────────────────
    if mode == "original":
        logger.info("[Rewriter] Mode is 'original', skipping rewrite.")
        return {
            **state,
            "original_query": original,
            "rewritten_query": original,
            "user_query": original,
        }

    # ── Generate rewritten version (needed for both 'auto' and 'ask') ─────────
    try:
        provider = GroqProvider(model_id="llama-3.1-8b-instant")
        response = provider.call(
            prompt=original,
            system=REWRITE_SYSTEM_PROMPT,
            max_tokens=256,
        )
        rewritten = response.content.strip()

        if not rewritten or len(rewritten) < 3:
            rewritten = original

        logger.info(f"[Rewriter] Rewritten query: {rewritten}")

    except Exception as e:
        logger.error(f"[Rewriter] Failed: {e}. Keeping original query.")
        rewritten = original

    # ── Mode: ask — pause here, let UI decide which to use ─────────────────────
    if mode == "ask":
        logger.info("[Rewriter] Mode is 'ask', pausing for user decision.")
        return {
            **state,
            "original_query": original,
            "rewritten_query": rewritten,
            "rewrite_pending_decision": True,
            # user_query stays as original until user picks
        }

    # ── Mode: auto — use rewritten immediately ──────────────────────────────────
    return {
        **state,
        "original_query": original,
        "rewritten_query": rewritten,
        "user_query": rewritten,
        "rewrite_pending_decision": False,
    }
