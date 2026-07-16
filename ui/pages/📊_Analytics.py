import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.export import export_full_session_report

st.set_page_config(page_title="Analytics — TieredFlow", page_icon="📊", layout="wide")

st.title("📊 Analytics")
st.caption("Current session performance metrics")
st.divider()

# ── Guard — no data yet ───────────────────────────────────────────────────────

if "messages" not in st.session_state or not st.session_state.get("messages"):
    st.info("No data yet — head to the Chat page and send some queries first.")
    st.stop()

# ── Build dataframe from session messages ─────────────────────────────────────

records = []
call_number = 0

for msg in st.session_state.messages:
    if msg["role"] == "assistant" and "meta" in msg:
        call_number += 1
        meta = msg["meta"]
        records.append(
            {
                "call_number": call_number,
                "query": st.session_state.messages[
                    st.session_state.messages.index(msg) - 1
                ]["content"][:60],
                "task_type": str(meta.get("task_type", "—")).replace("TaskType.", ""),
                "tier": str(meta.get("selected_tier", "—")).replace("Tier.", ""),
                "cost_usd": meta.get("cost_usd") or 0.0,
                "latency_ms": meta.get("latency_ms") or 0,
                "served_from_cache": meta.get("served_from_cache", False),
                "tokens_input": meta.get("tokens_used_input") or 0,
                "tokens_output": meta.get("tokens_used_output") or 0,
            }
        )

if not records:
    st.info("No LLM calls yet in this session.")
    st.stop()

df = pd.DataFrame(records)

# ── Report Downloader ───────────────────────────────────────────────────────────────
st.subheader("📥 Export Session Report")

call_log = st.session_state.get("messages", [])
# Pull call_log entries from the actual graph result metadata stored in messages
all_call_logs = []
for msg in st.session_state.get("messages", []):
    if msg.get("role") == "assistant" and "meta" in msg:
        entries = msg["meta"].get("call_log", [])
        all_call_logs.extend(entries)

if all_call_logs:
    csv_data = export_full_session_report(
        session_id=st.session_state.session_id,
        call_log=all_call_logs,
        total_cost=st.session_state.total_cost,
        total_calls=len(all_call_logs),
    )

    st.download_button(
        label="⬇️ Download Session Report (CSV)",
        data=csv_data,
        file_name=f"tieredflow_session_{st.session_state.session_id}.csv",
        mime="text/csv",
        use_container_width=True,
    )
else:
    st.caption("No calls yet in this session to export.")

# ── Top metrics ───────────────────────────────────────────────────────────────
st.divider()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Calls", len(df))
m2.metric("Total Cost", f"${df['cost_usd'].sum():.6f}")
m3.metric("Avg Cost/Query", f"${df['cost_usd'].mean():.6f}")
m4.metric("Avg Latency", f"{df['latency_ms'].mean():.0f}ms")
m5.metric("Cache Hit Rate", f"{df['served_from_cache'].mean():.0%}")

st.divider()

# ── Row 1 — Cost + Tier distribution ─────────────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    fig_cost = px.bar(
        df,
        x="call_number",
        y="cost_usd",
        color="tier",
        title="Cost per Query",
        labels={"call_number": "Call #", "cost_usd": "Cost (USD)", "tier": "Tier"},
        color_discrete_map={
            "ultra_cheap": "#22c55e",
            "mid": "#f59e0b",
            "quality": "#3b82f6",
            "power": "#ef4444",
        },
    )
    fig_cost.update_layout(showlegend=True)
    st.plotly_chart(fig_cost, use_container_width=True)

with col2:
    tier_counts = df["tier"].value_counts().reset_index()
    tier_counts.columns = ["tier", "count"]
    fig_tier = px.pie(
        tier_counts,
        names="tier",
        values="count",
        title="Tier Distribution",
        color="tier",
        color_discrete_map={
            "ultra_cheap": "#22c55e",
            "mid": "#f59e0b",
            "quality": "#3b82f6",
            "power": "#ef4444",
            "None": "#94a3b8",
        },
    )
    st.plotly_chart(fig_tier, use_container_width=True)

# ── Row 2 — Latency + Cache ───────────────────────────────────────────────────

col3, col4 = st.columns(2)

with col3:
    fig_latency = px.bar(
        df,
        x="call_number",
        y="latency_ms",
        color="tier",
        title="Latency per Query (ms)",
        labels={"call_number": "Call #", "latency_ms": "Latency (ms)"},
        color_discrete_map={
            "ultra_cheap": "#22c55e",
            "mid": "#f59e0b",
            "quality": "#3b82f6",
            "power": "#ef4444",
        },
    )
    st.plotly_chart(fig_latency, use_container_width=True)

with col4:
    cache_counts = df["served_from_cache"].value_counts().reset_index()
    cache_counts.columns = ["served_from_cache", "count"]
    cache_counts["label"] = cache_counts["served_from_cache"].map(
        {True: "Cache Hit", False: "Fresh Call"}
    )
    fig_cache = px.pie(
        cache_counts,
        names="label",
        values="count",
        title="Cache Hit vs Fresh Call",
        color="label",
        color_discrete_map={
            "Cache Hit": "#22c55e",
            "Fresh Call": "#3b82f6",
        },
        hole=0.4,
    )
    st.plotly_chart(fig_cache, use_container_width=True)

# ── Row 3 — Token usage ───────────────────────────────────────────────────────

st.divider()
st.subheader("🔢 Token Usage")

fig_tokens = go.Figure(
    data=[
        go.Bar(
            name="Input Tokens",
            x=df["call_number"],
            y=df["tokens_input"],
            marker_color="#3b82f6",
        ),
        go.Bar(
            name="Output Tokens",
            x=df["call_number"],
            y=df["tokens_output"],
            marker_color="#f59e0b",
        ),
    ]
)
fig_tokens.update_layout(
    barmode="group",
    title="Input vs Output Tokens per Query",
    xaxis_title="Call #",
    yaxis_title="Tokens",
)
st.plotly_chart(fig_tokens, use_container_width=True)

# ── Call log table ────────────────────────────────────────────────────────────

st.divider()
st.subheader("📋 Call Log")
st.dataframe(df, use_container_width=True, hide_index=True)
