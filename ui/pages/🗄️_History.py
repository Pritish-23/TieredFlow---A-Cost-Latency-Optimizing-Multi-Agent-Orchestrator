import pandas as pd
import plotly.express as px
import streamlit as st

from memory.store import get_store
from utils.export import export_session_messages_to_csv

st.set_page_config(page_title="History — TieredFlow", page_icon="🗄️", layout="wide")

st.title("🗄️ History")
st.caption("All past sessions with full conversation view")
st.divider()

store = get_store()
sessions = store.get_all_sessions()

if not sessions:
    st.info("No past sessions found. Head to Chat and send some queries!")
    st.stop()

# ── Session list ──────────────────────────────────────────────────────────────

st.subheader(f"📁 {len(sessions)} Session(s) Found")

for session in sessions:
    with st.expander(
        f"🗂️ Session `{session.session_id}` — "
        f"{session.total_messages} messages — "
        f"${session.total_cost_usd:.6f} — "
        f"{session.last_active[:10]}"
    ):
        messages = store.get_session_messages(session.session_id)

        if not messages:
            st.write("No messages in this session.")
            continue

        # ── Per-session mini analytics ─────────────────────────────────────────

        df = pd.DataFrame(
            [
                {
                    "task_type": m.task_type.replace("TaskType.", ""),
                    "tier": m.tier.replace("Tier.", ""),
                    "cost_usd": m.cost_usd,
                    "latency_ms": m.latency_ms,
                    "served_from_cache": bool(m.served_from_cache),
                }
                for m in messages
            ]
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Messages", len(messages))
        m2.metric("Total Cost", f"${df['cost_usd'].sum():.6f}")
        m3.metric("Avg Latency", f"{df['latency_ms'].mean():.0f}ms")
        m4.metric("Cache Hit Rate", f"{df['served_from_cache'].mean():.0%}")

        # Mini charts
        col1, col2 = st.columns(2)

        with col1:
            tier_counts = df["tier"].value_counts().reset_index()
            tier_counts.columns = ["tier", "count"]
            fig = px.pie(
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
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.bar(
                df,
                y="cost_usd",
                title="Cost per Message",
                labels={"index": "Message #", "cost_usd": "Cost (USD)"},
                color="tier",
                color_discrete_map={
                    "ultra_cheap": "#22c55e",
                    "mid": "#f59e0b",
                    "quality": "#3b82f6",
                    "power": "#ef4444",
                },
            )
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # ── Full conversation ──────────────────────────────────────────────────

        st.subheader("💬 Conversation")

        for msg in messages:
            with st.chat_message("user"):
                st.markdown(msg.user_query)

            with st.chat_message("assistant"):
                st.markdown(msg.response)
                cols = st.columns(5)
                cols[0].caption(
                    f"🧠 **Task:** {msg.task_type.replace('TaskType.', '')}"
                )
                cols[1].caption(f"⚡ **Tier:** {msg.tier.replace('Tier.', '')}")
                cols[2].caption(f"💰 **Cost:** ${msg.cost_usd:.6f}")
                cols[3].caption(f"⏱️ **Latency:** {msg.latency_ms}ms")
                cols[4].caption(
                    f"{'🟢 Cache hit' if msg.served_from_cache else '🔵 Fresh call'}"
                )

        # ── Export session ─────────────────────────────────────────────────────

        st.divider()

        csv_data = export_session_messages_to_csv(messages, session.session_id)
        st.download_button(
            label="⬇️ Export Session (CSV)",
            data=csv_data,
            file_name=f"tieredflow_history_{session.session_id}.csv",
            mime="text/csv",
            key=f"export_{session.session_id}",
            use_container_width=True,
        )

        # ── Delete session ─────────────────────────────────────────────────────

        st.divider()
        if st.button(
            f"🗑️ Delete Session {session.session_id}", key=f"del_{session.session_id}"
        ):
            store.delete_session(session.session_id)
            st.success(f"Session {session.session_id} deleted.")
            st.rerun()
