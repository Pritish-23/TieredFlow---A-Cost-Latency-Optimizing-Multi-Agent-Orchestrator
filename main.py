import argparse
import logging
import sys
import uuid

from config.settings import settings
from core.graph import graph
from core.state import initial_state
from memory.store import get_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def run_query(query: str, budget: float = None) -> dict:
    budget = budget or settings.default_budget_usd
    session_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": session_id}}

    state = initial_state(query, session_id, budget)
    final = graph.invoke(state, config=config)

    # Save to persistent store
    store = get_store()
    store.create_session(session_id)
    store.save_message(
        session_id=session_id,
        user_query=query,
        response=final.get("final_response", ""),
        task_type=str(final.get("task_type", "")),
        tier=str(final.get("selected_tier", "")),
        model_id=str(final.get("llm_response", "")),
        cost_usd=final.get("cost_usd") or 0.0,
        latency_ms=final.get("latency_ms") or 0,
        served_from_cache=final.get("served_from_cache", False),
    )

    return final


def main():
    parser = argparse.ArgumentParser(description="TieredFlow")
    parser.add_argument("query", nargs="?", default=None)
    parser.add_argument("--budget", type=float, default=None)
    args = parser.parse_args()

    query = args.query or input("Enter your query: ").strip()
    if not query:
        print("No query provided.")
        sys.exit(1)

    print(f"\n{'─'*60}")
    print(f"Query: {query}")
    print(f"{'─'*60}")

    result = run_query(query, args.budget)

    print(f"\n✅ Response:\n{result.get('final_response', 'No response.')}")
    print(f"\n{'─'*60}")
    print("📊 Routing Summary")
    print(f"  Task type:         {result.get('task_type')}")
    print(f"  Tier selected:     {result.get('selected_tier')}")
    print(f"  Served from cache: {result.get('served_from_cache')}")
    print(f"  Cost:              ${result.get('cost_usd', 0):.6f}")
    print(f"  Latency:           {result.get('latency_ms', '—')}ms")
    print(f"  Budget remaining:  ${result.get('budget_remaining_usd', 0):.4f}")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
