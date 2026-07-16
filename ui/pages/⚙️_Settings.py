import os

import pandas as pd
import streamlit as st

from config.constants import MODELS
from memory.store import get_store

st.set_page_config(page_title="Settings — TieredFlow", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")
st.caption("Configure TieredFlow behaviour")
st.divider()


# ── Budget ────────────────────────────────────────────────────────────────────

st.subheader("💰 Budget")

budget = st.slider(
    "Default session budget (USD)",
    min_value=0.10,
    max_value=10.00,
    value=st.session_state.get("budget", 1.00),
    step=0.10,
    format="$%.2f",
)

if st.button("💾 Save Budget", type="primary"):
    st.session_state.budget = budget
    st.success(f"Budget updated to ${budget:.2f}")

st.divider()


# ── Cache thresholds ──────────────────────────────────────────────────────────

st.subheader("🧠 Semantic Cache Thresholds")

st.markdown("""
- **High threshold** — queries above this are auto-served from cache with no interruption
- **Mid threshold** — queries between mid and high trigger a human approval prompt
- **Below mid** — cache is skipped entirely, fresh LLM call is made
""")

col1, col2 = st.columns(2)

with col1:
    cache_high = st.slider(
        "High similarity threshold (auto-serve)",
        min_value=0.80,
        max_value=1.00,
        value=st.session_state.get("cache_high", 0.92),
        step=0.01,
    )

with col2:
    cache_mid = st.slider(
        "Mid similarity threshold (HITL)",
        min_value=0.50,
        max_value=0.90,
        value=st.session_state.get("cache_mid", 0.75),
        step=0.01,
    )

if cache_mid >= cache_high:
    st.error("Mid threshold must be lower than high threshold.")
else:
    if st.button("💾 Save Cache Settings", type="primary"):
        st.session_state.cache_high = cache_high
        st.session_state.cache_mid = cache_mid
        st.success("Cache thresholds updated.")

st.divider()


# ── Model preferences ─────────────────────────────────────────────────────────

st.subheader("🤖 Model Tiers")
st.markdown("Current tier → model mapping:")

tier_data = []
for tier, meta in MODELS.items():
    tier_data.append(
        {
            "Tier": tier.value,
            "Model": meta.model_id,
            "Provider": meta.provider,
            "Cost/1K Input": f"${meta.cost_per_1k_input:.5f}",
            "Cost/1K Output": f"${meta.cost_per_1k_output:.5f}",
            "Avg Latency": f"{meta.avg_latency_ms}ms",
        }
    )


st.dataframe(pd.DataFrame(tier_data), use_container_width=True, hide_index=True)

st.divider()

# ── Query Rewriting ─────────────────────────────────────────────────────────

st.subheader("🔄 Query Rewriting")

query_mode_labels = {
    "auto": "Auto (always use rewritten query)",
    "original": "Always use original query (skip rewriting)",
    "ask": "Ask me each time",
}

current_mode = st.session_state.get("query_mode", "auto")

selected_label = st.radio(
    "How should TieredFlow handle query rewriting?",
    options=list(query_mode_labels.values()),
    index=list(query_mode_labels.keys()).index(current_mode),
)

# Map back to internal value
selected_mode = [k for k, v in query_mode_labels.items() if v == selected_label][0]
st.session_state.query_mode = selected_mode

st.caption(f"Current mode: `{selected_mode}`")


# ── LangSmith ─────────────────────────────────────────────────────────────────

st.subheader("🔍 Observability")

tracing = st.toggle(
    "Enable LangSmith tracing",
    value=st.session_state.get("langsmith_tracing", True),
)

if tracing != st.session_state.get("langsmith_tracing", True):
    st.session_state.langsmith_tracing = tracing
    os.environ["LANGCHAIN_TRACING_V2"] = str(tracing).lower()
    st.success(f"LangSmith tracing {'enabled' if tracing else 'disabled'}.")

st.divider()


# ── Danger zone ───────────────────────────────────────────────────────────────

st.subheader("🚨 Danger Zone")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Reset Current Session", use_container_width=True):
        for key in ["messages", "total_cost", "session_id"]:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Session reset. Head to Chat to start fresh.")

with col2:
    if st.button("🗑️ Delete ALL History", use_container_width=True, type="primary"):
        confirm = st.session_state.get("confirm_delete", False)
        st.session_state.confirm_delete = True
        st.warning("Click again to confirm deleting ALL sessions permanently.")

if st.session_state.get("confirm_delete"):
    if st.button("⚠️ Yes, delete everything", type="primary"):
        store = get_store()
        sessions = store.get_all_sessions()
        for s in sessions:
            store.delete_session(s.session_id)
        st.session_state.confirm_delete = False
        st.success("All history deleted.")
        st.rerun()
