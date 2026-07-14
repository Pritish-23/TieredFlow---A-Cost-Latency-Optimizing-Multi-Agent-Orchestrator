import uuid
import streamlit as st
import plotly.express as px
import pandas as pd

from core.graph import graph
from core.state import initial_state
from config.constants import Tier
from config.settings import settings


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TieredFlow",
    page_icon="🎛️",
    layout="wide",
)


# ── Session state init ────────────────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "call_log" not in st.session_state:
    st.session_state.call_log = []

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

if "budget" not in st.session_state:
    st.session_state.budget = settings.default_budget_usd

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🎛️ TieredFlow")
st.caption("Cost/Latency-Aware Multi-Agent LLM Orchestrator")
st.divider()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Session Config")

    budget = st.slider(
        "Budget (USD)",
        min_value=0.10,
        max_value=5.00,
        value=st.session_state.budget,
        step=0.10,
        format="$%.2f",
    )
    st.session_state.budget = budget

    st.divider()
    st.metric("Session ID", st.session_state.session_id)
    st.metric("Total Calls", len(st.session_state.call_log))
    st.metric("Total Cost", f"${st.session_state.total_cost:.6f}")
    st.metric(
        "Budget Remaining",
        f"${max(budget - st.session_state.total_cost, 0):.4f}"
    )

    if st.button("🔄 Reset Session"):
        for key in ["session_id", "call_log", "total_cost", "last_result"]:
            del st.session_state[key]
        st.rerun()


# ── Query input ───────────────────────────────────────────────────────────────

st.subheader("💬 Query")

query = st.text_area(
    "Enter your query",
    placeholder="e.g. Summarize what machine learning is in simple terms",
    height=100,
    label_visibility="collapsed",
)

col1, col2 = st.columns([1, 5])
with col1:
    submit = st.button("⚡ Run", type="primary", use_container_width=True)


# ── Run graph on submit ───────────────────────────────────────────────────────

if submit and query.strip():
    with st.spinner("Running through TieredFlow graph..."):
        thread_id = f"{st.session_state.session_id}-{len(st.session_state.call_log)}"
        config = {"configurable": {"thread_id": thread_id}}
        state = initial_state(
            query.strip(),
            st.session_state.session_id,
            max(budget - st.session_state.total_cost, 0.0),
        )

        result = graph.invoke(state, config=config)
        st.session_state.last_result = result

        if result.get("cost_usd"):
            st.session_state.total_cost += result["cost_usd"]

        if result.get("call_log"):
            st.session_state.call_log.extend(result["call_log"])

elif submit and not query.strip():
    st.warning("Please enter a query.")


# ── Response panel ────────────────────────────────────────────────────────────

if st.session_state.last_result:
    result = st.session_state.last_result
    st.divider()

    # Cache badge
    if result.get("served_from_cache"):
        st.success("⚡ Served from semantic cache — $0.00 cost")
    else:
        st.info("🤖 Fresh LLM response")

    st.subheader("✅ Response")
    st.markdown(result.get("final_response", "No response."))

    # Routing summary
    st.divider()
    st.subheader("📊 Routing Decision")

    m1, m2, m3, m4, m5 = st.columns(5)
    cost = result.get("cost_usd") or 0.0
    latency = result.get("latency_ms")

    m1.metric("Task Type",  str(result.get("task_type",     "—")).replace("TaskType.", ""))
    m2.metric("Tier",       str(result.get("selected_tier", "—")).replace("Tier.", ""))
    m3.metric("Cost",       f"${cost:.6f}")
    m4.metric("Latency",    f"{latency}ms" if latency else "—")
    m5.metric("From Cache", "Yes" if result.get("served_from_cache") else "No")

    if result.get("routing_reason"):
        st.caption(f"Routing reason: {result['routing_reason']}")


# ── Session analytics ─────────────────────────────────────────────────────────

if st.session_state.call_log:
    st.divider()
    st.subheader("📈 Session Analytics")

    df = pd.DataFrame(st.session_state.call_log)

    col_left, col_right = st.columns(2)

    with col_left:
        fig_cost = px.bar(
            df,
            x="call_number",
            y="cost_usd",
            color="tier",
            title="Cost per Query",
            labels={"call_number": "Call #", "cost_usd": "Cost (USD)"},
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    with col_right:
        tier_counts = df["tier"].value_counts().reset_index()
        tier_counts.columns = ["tier", "count"]
        fig_tier = px.pie(
            tier_counts,
            names="tier",
            values="count",
            title="Tier Distribution",
        )
        st.plotly_chart(fig_tier, use_container_width=True)

    # Call log table
    st.subheader("📋 Call Log")
    display_cols = ["call_number", "query_snippet", "task_type", "tier",
                    "model_id", "input_tokens", "output_tokens", "cost_usd",
                    "latency_ms", "served_from_cache"]
    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
    )