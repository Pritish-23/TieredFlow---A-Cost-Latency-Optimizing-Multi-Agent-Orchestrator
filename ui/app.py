import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="TieredFlow",
    page_icon="🎛️",
    layout="wide",
)

st.title("🎛️ TieredFlow")
st.caption("Cost/Latency-Aware Multi-Agent LLM Orchestrator")
st.divider()

st.markdown("""
### Welcome to TieredFlow

TieredFlow intelligently routes your queries to the most cost-effective
LLM based on task complexity, budget, and semantic cache hits.

**Navigate using the sidebar to get started.**
""")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info(
        "💬 **Chat**\nSend queries and get responses with full routing transparency"
    )

with col2:
    st.info(
        "📊 **Analytics**\nTrack cost, latency and tier distribution for current session"
    )

with col3:
    st.info("🗄️ **History**\nBrowse past sessions with per-session analysis")

with col4:
    st.info("⚙️ **Settings**\nConfigure budget, cache thresholds and preferences")
