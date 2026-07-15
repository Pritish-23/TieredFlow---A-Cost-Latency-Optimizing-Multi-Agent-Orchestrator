import uuid

import streamlit as st

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
            cols[3].caption(f"⏱️ **Latency:** {latency}ms" if latency else "⏱️ **Latency:** —")
            cols[4].caption(f"{'🟢 Cache hit' if cached else '🔵 Fresh call'}")
            cols[5].caption(confidence_badge)


# ── Query input ───────────────────────────────────────────────────────────────

query = st.chat_input("Ask anything...")

if query:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Run graph
    with st.chat_message("assistant"):
        thread_id = f"{st.session_state.session_id}-{len(st.session_state.messages)}"
        config = {"configurable": {"thread_id": thread_id}}
        state = initial_state(
            query,
            st.session_state.session_id,
            max(st.session_state.budget - st.session_state.total_cost, 0.0),
        )

        with st.spinner("Routing query..."):
            result = graph.invoke(state, config=config)

            # state_snapshot = graph.get_state(config)
            # st.write(f"DEBUG snapshot confidence: {state_snapshot.values.get('confidence_score')}")
            # st.write(f"DEBUG result confidence: {result.get('confidence_score')}")
            # if state_snapshot and state_snapshot.values:
            #     result = {**result, **state_snapshot.values}

        response = result.get("final_response", "No response.")

        if result.get("served_from_cache"):
            # Instant display for cache hits
            st.markdown(response)
        else:
            # Stream fresh LLM response
            from providers import get_provider

            tier = result.get("selected_tier")
            provider = get_provider(tier)
            system = (
                result.get("system_prompt") or "You are a helpful, concise assistant."
            )
            prompt = result.get("rewritten_query") or query

            def stream_response():
                for chunk in provider.stream(
                    prompt=prompt,
                    system=system,
                    max_tokens=1024,
                ):
                    yield chunk

            response = st.write_stream(stream_response())

        # Metadata badge
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
        cols[3].caption(f"⏱️ **Latency:** {latency}ms" if latency else "⏱️ **Latency:** —")
        cols[4].caption(f"{'🟢 Cache hit' if cached else '🔵 Fresh call'}")
        cols[5].caption(confidence_badge)

    # Update session state
    st.session_state.total_cost += cost
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "meta": result,
        }
    )

    # Save to persistent store
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
