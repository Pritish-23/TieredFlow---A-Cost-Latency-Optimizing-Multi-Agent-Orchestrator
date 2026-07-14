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

    logger.info(f"[Rewriter] Original query: {original}")

    try:
        provider = GroqProvider(model_id="llama-3.1-8b-instant")
        response = provider.call(
            prompt=original,
            system=REWRITE_SYSTEM_PROMPT,
            max_tokens=256,
        )
        rewritten = response.content.strip()

        # Safety check — if rewritten is too different or empty, keep original
        if not rewritten or len(rewritten) < 3:
            rewritten = original

        logger.info(f"[Rewriter] Rewritten query: {rewritten}")

    except Exception as e:
        logger.error(f"[Rewriter] Failed: {e}. Keeping original query.")
        rewritten = original

    return {
        **state,
        "original_query": original,
        "rewritten_query": rewritten,
        "user_query": rewritten,
    }