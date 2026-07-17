import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from memory.store import get_store
get_store()  # ensures DB + tables exist regardless of which page loads first

import uuid
import time

import streamlit as st
from langgraph.types import Command

from config.settings import settings
from core.graph import graph
from core.state import initial_state
from memory.store import get_store

st.set_page_config(page_title="Chat — TieredFlow", page_icon="💬", layout="wide")

# ── Session state init ────────────────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "messages" not in st.session_state:
    st.session_state.messages = []

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

if "budget" not in st.session_state:
    st.session_state.budget = settings.default_budget_usd

if "query_mode" not in st.session_state:
    st.session_state.query_mode = "auto"

if "pending_cache_decision" not in st.session_state:
    st.session_state.pending_cache_decision = None

if "pending_tier_override" not in st.session_state:
    st.session_state.pending_tier_override = None

if "pending_rewrite" not in st.session_state:
    st.session_state.pending_rewrite = None


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Session")
    st.metric("Session ID", st.session_state.session_id)

    budget_remaining = max(st.session_state.budget - st.session_state.total_cost, 0.0)
    st.metric("Budget Remaining", f"${budget_remaining:.4f}")
    st.metric("Total Cost", f"${st.session_state.total_cost:.6f}")
    st.metric("Total Messages", len(st.session_state.messages))

    st.divider()

    # Budget gauge
    budget_pct = 1.0 - (budget_remaining / st.session_state.budget)
    st.progress(min(budget_pct, 1.0), text=f"Budget used: {budget_pct:.0%}")

    st.divider()

    if st.button("🆕 New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages = []
        st.session_state.total_cost = 0.0
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────

st.title("💬 Chat")
st.caption(f"Session: `{st.session_state.session_id}`")
st.divider()


# ── Chat history ──────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and "meta" in msg:
            meta = msg["meta"]
            # cols = st.columns(5)

            task = str(meta.get("task_type", "—")).replace("TaskType.", "")
            tier = str(meta.get("selected_tier", "—")).replace("Tier.", "")
            cost = meta.get("cost_usd") or 0.0
            latency = meta.get("latency_ms")
            cached = meta.get("served_from_cache", False)

            score = msg.get("meta", {}).get("confidence_score")
            if score is None:
                confidence_badge = "⚪ Confidence: —"
            elif score >= 8:
                confidence_badge = f"🟢 Confidence: {score}/10"
            elif score >= 5:
                confidence_badge = f"🟡 Confidence: {score}/10"
            else:
                confidence_badge = f"🔴 Confidence: {score}/10"

            cols = st.columns(6)
            cols[0].caption(f"🧠 **Task:** {task}")
            cols[1].caption(f"⚡ **Tier:** {tier}")
            cols[2].caption(f"💰 **Cost:** ${cost:.6f}")
            cols[3].caption(
                f"⏱️ **Latency:** {latency}ms" if latency else "⏱️ **Latency:** —"
            )
            cols[4].caption(f"{'🟢 Cache hit' if cached else '🔵 Fresh call'}")
            cols[5].caption(confidence_badge)


# ── Query input ───────────────────────────────────────────────────────────────

query = st.chat_input("Ask anything...")

if query and not st.session_state.pending_rewrite:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    thread_id = st.session_state.session_id
    config = {"configurable": {"thread_id": thread_id}}
    state = initial_state(
        query,
        st.session_state.session_id,
        max(st.session_state.budget - st.session_state.total_cost, 0.0),
        query_mode=st.session_state.get("query_mode", "auto"),
        conversation_history=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[-10:]  # last 10 messages (5 turns)
        ],
    )

    with st.spinner("Routing query..."):
        result = graph.invoke(state, config=config)

    state_snapshot = graph.get_state(config)

    if state_snapshot.next and "human_cache_decision" in state_snapshot.next:
        st.session_state.pending_cache_decision = {
            "thread_id": thread_id,
            "config": config,
            "cached_response": state_snapshot.values.get("cached_response"),
            "similarity": state_snapshot.values.get("cache_similarity_score"),
            "query": query,
        }
        st.rerun()

    elif state_snapshot.next and "human_tier_override" in state_snapshot.next:
        st.session_state.pending_tier_override = {
            "thread_id": thread_id,
            "config": config,
            "current_tier": state_snapshot.values.get("selected_tier"),
            "routing_reason": state_snapshot.values.get("routing_reason"),
            "budget_remaining": state_snapshot.values.get("budget_remaining_usd"),
            "query": query,
        }
        st.rerun()

    elif state_snapshot.next and "human_rewrite_decision" in state_snapshot.next:
        st.session_state.pending_rewrite = {
            "thread_id": thread_id,
            "config": config,
            "original": state_snapshot.values.get("original_query"),
            "rewritten": state_snapshot.values.get("rewritten_query"),
            "query": query,
        }
        st.rerun()

    else:
        st.session_state._last_result = result
        st.session_state._last_query = query

# ── Handle pending rewrite decision (persists across reruns) ──────────────────

if st.session_state.pending_rewrite:
    pending = st.session_state.pending_rewrite

    with st.chat_message("assistant"):
        st.info(
            "🔄 The query rewriter suggests a clearer version. Which would you like to use?"
        )
        col1, col2 = st.columns(2)
        with col1:
            st.caption("**Original**")
            st.write(pending["original"])
        with col2:
            st.caption("**Rewritten**")
            st.write(pending["rewritten"])

        choice = st.radio(
            "Choose which query to proceed with:",
            options=["Rewritten (recommended)", "Original"],
            key=f"rewrite_choice_{pending['thread_id']}",
        )

        if st.button("Continue", key=f"continue_{pending['thread_id']}"):
            picked = "rewritten" if choice.startswith("Rewritten") else "original"
            with st.spinner("Processing..."):
                result = graph.invoke(
                    Command(resume={"choice": picked}),
                    config=pending["config"],
                )
            st.session_state._last_result = result
            st.session_state._last_query = pending["query"]
            st.session_state.pending_rewrite = None
            st.rerun()

# ── Handle pending cache decision ──────────────────────────────────────────────

if "pending_cache_decision" not in st.session_state:
    st.session_state.pending_cache_decision = None

if st.session_state.pending_cache_decision:
    pending = st.session_state.pending_cache_decision

    with st.chat_message("assistant"):
        similarity = pending["similarity"] or 0
        st.info(f"🗄️ Found a similar cached response ({similarity:.0%} match). Use it?")
        st.caption("**Cached response preview:**")
        preview = pending["cached_response"] or ""
        st.write(preview[:300] + "..." if len(preview) > 300 else preview)

        choice = st.radio(
            "What would you like to do?",
            options=["Use cached response", "Get a fresh answer"],
            key=f"cache_choice_{pending['thread_id']}",
        )

        if st.button("Continue", key=f"cache_continue_{pending['thread_id']}"):
            decision = "accept" if choice.startswith("Use cached") else "reject"
            with st.spinner("Processing..."):
                result = graph.invoke(
                    Command(resume={"decision": decision}),
                    config=pending["config"],
                )
            st.session_state._last_result = result
            st.session_state._last_query = pending["query"]
            st.session_state.pending_cache_decision = None

            # Check if resuming led to another interrupt (e.g. tier override)
            snap = graph.get_state(pending["config"])
            if snap.next and "human_tier_override" in snap.next:
                st.session_state.pending_tier_override = {
                    "thread_id": pending["thread_id"],
                    "config": pending["config"],
                    "current_tier": snap.values.get("selected_tier"),
                    "routing_reason": snap.values.get("routing_reason"),
                    "budget_remaining": snap.values.get("budget_remaining_usd"),
                    "query": pending["query"],
                }
                st.session_state._last_result = None
            st.rerun()


# ── Handle pending tier override ───────────────────────────────────────────────

if "pending_tier_override" not in st.session_state:
    st.session_state.pending_tier_override = None

if st.session_state.pending_tier_override:
    pending = st.session_state.pending_tier_override

    with st.chat_message("assistant"):
        st.info(
            f"⚡ Router selected tier **{pending['current_tier']}** "
            f"({pending['routing_reason']}). Override?"
        )
        st.caption(f"Budget remaining: ${pending['budget_remaining']:.4f}")

        tier_options = ["ULTRA_CHEAP", "MID", "QUALITY", "POWER"]
        chosen = st.radio(
            "Choose tier:",
            options=tier_options,
            index=(
                tier_options.index(str(pending["current_tier"]).replace("Tier.", ""))
                if str(pending["current_tier"]).replace("Tier.", "") in tier_options
                else 0
            ),
            key=f"tier_choice_{pending['thread_id']}",
        )

        if st.button("Continue", key=f"tier_continue_{pending['thread_id']}"):
            with st.spinner("Processing..."):
                result = graph.invoke(
                    Command(resume={"tier": chosen}),
                    config=pending["config"],
                )
            st.session_state._last_result = result
            st.session_state._last_query = pending["query"]
            st.session_state.pending_tier_override = None
            st.rerun()

# ── Display result (runs after either direct completion or resumed decision) ──

if st.session_state.get("_last_result"):
    result = st.session_state._last_result
    query = st.session_state._last_query

    with st.chat_message("assistant"):
        response = result.get("final_response") or "⚠️ No response was generated. Please try rephrasing your query."

        if result.get("served_from_cache"):
            st.markdown(response)

        else:
            # Simulate streaming using the response we already have
            # (avoids a redundant second LLM API call)
            def fake_stream():
                words = response.split(" ")
                for word in words:
                    yield word + " "
                    time.sleep(0.015)  # tune this for typing speed

            st.write_stream(fake_stream())

        meta = result
        task = str(meta.get("task_type", "—")).replace("TaskType.", "")
        tier = str(meta.get("selected_tier", "—")).replace("Tier.", "")
        cost = meta.get("cost_usd") or 0.0
        latency = meta.get("latency_ms")
        cached = meta.get("served_from_cache", False)

        call_log = result.get("call_log", [])
        score = call_log[-1].get("confidence_score") if call_log else None
        if score is None:
            confidence_badge = "⚪ Confidence: —"
        elif score >= 8:
            confidence_badge = f"🟢 Confidence: {score}/10"
        elif score >= 5:
            confidence_badge = f"🟡 Confidence: {score}/10"
        else:
            confidence_badge = f"🔴 Confidence: {score}/10"

        cols = st.columns(6)
        cols[0].caption(f"🧠 **Task:** {task}")
        cols[1].caption(f"⚡ **Tier:** {tier}")
        cols[2].caption(f"💰 **Cost:** ${cost:.6f}")
        cols[3].caption(
            f"⏱️ **Latency:** {latency}ms" if latency else "⏱️ **Latency:** —"
        )
        cols[4].caption(f"{'🟢 Cache hit' if cached else '🔵 Fresh call'}")
        cols[5].caption(confidence_badge)

    st.session_state.total_cost += cost
    st.session_state.messages.append(
        {"role": "assistant", "content": response, "meta": result}
    )

    store = get_store()
    store.create_session(st.session_state.session_id)
    store.save_message(
        session_id=st.session_state.session_id,
        user_query=query,
        response=response,
        task_type=str(result.get("task_type", "")),
        tier=str(result.get("selected_tier", "")),
        model_id=str(result.get("tokens_used_input", "")),
        cost_usd=cost,
        latency_ms=result.get("latency_ms") or 0,
        served_from_cache=cached,
    )

    # Clear so it doesn't redisplay on next natural rerun
    st.session_state._last_result = None
