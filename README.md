# 🎛️ TieredFlow

**A Cost/Latency-Aware Multi-Agent LLM Orchestrator built with LangGraph**

TieredFlow intelligently routes user queries across a 4-tier model lineup based on task complexity, live budget, and semantic cache hits — while keeping a human in the loop for every routing decision that matters. It's designed to answer a question every production LLM system eventually has to: *when is it worth paying more for a smarter model?*

---

## 🧠 Why TieredFlow

Most LLM demos call one model for everything. TieredFlow instead treats **cost, latency, and correctness** as first-class constraints, and makes routing decisions transparent and overridable rather than hidden inside a black box:

- **4-tier routing** — classifies each query's task type via an LLM classifier, then routes to the cheapest tier that can handle it (ultra-cheap Groq Llama for classification/extraction, up to Claude Sonnet for deep reasoning)
- **Semantic cache with tiered trust** — near-duplicate queries are served from cache automatically at high similarity, prompt a human decision at medium similarity, and skip the cache entirely below that
- **Full human-in-the-loop (HITL) control** — three separate interrupt points (cache-serve decision, tier override, query-rewrite choice) let a human step in before any cost is incurred
- **Self-correcting hallucination fallback** — when a knowledge tool (e.g. Wikipedia) comes up empty, the system automatically falls back to web search **combined with** the model's own knowledge, rather than either hallucinating or refusing
- **Confidence scoring** — every fresh LLM response is self-scored 1–10 by a second, cheap model call, surfaced directly in the UI
- **Persistent conversational memory** — SQLite-backed conversation history and session storage that survives restarts

---

## 🏗️ Architecture

```
                                   ┌─────────────┐
                                   │   START     │
                                   └──────┬──────┘
                                          ▼
                                   ┌─────────────┐
                                   │  Guardrail  │  (blocks jailbreaks, empty input)
                                   └──────┬──────┘
                                          ▼
                                   ┌─────────────┐
                                   │Task Classify│  (LLM classifier, keyword fallback)
                                   └──────┬──────┘
                                          ▼
                                   ┌─────────────┐
                                   │Cache Lookup │  (semantic similarity search)
                                   └──────┬──────┘
                        ┌─────────────────┼─────────────────┐
                        ▼                 ▼                 ▼
                 ┌─────────────┐  ┌───────────────┐  ┌─────────────┐
                 │ Auto-serve  │  │  Human Cache   │  │Query Rewriter│
                 │  (high sim) │  │  Decision (HITL)│  │ (mid/no sim)│
                 └──────┬──────┘  └───────┬────────┘  └──────┬──────┘
                        ▼                 ▼                  ▼
                       END          accept→END         ┌─────────────┐
                                    reject→rewriter     │Human Rewrite│
                                                         │Decision(opt)│
                                                         └──────┬──────┘
                                                                ▼
                                                         ┌─────────────┐
                                                         │   Router    │  (budget-aware tier selection)
                                                         └──────┬──────┘
                                                    ┌───────────┴──────────┐
                                                    ▼                      ▼
                                            ┌───────────────┐      ┌─────────────┐
                                            │Human Tier      │      │  LLM Call   │
                                            │Override (HITL) │─────▶│ + Tools     │
                                            └───────────────┘      │ + Confidence│
                                                                    │   Scoring   │
                                                                    └──────┬──────┘
                                                                           ▼
                                                                          END
```

### 4-Tier Model Lineup

| Tier | Model | Provider | Cost (in/out per 1K tokens) | Use case |
|------|-------|----------|------------------------------|----------|
| `ULTRA_CHEAP` | Llama 3.1 8B Instant | Groq | $0.00005 / $0.00008 | Classification, extraction, calculator, datetime |
| `MID` | Claude Haiku 4.5 | Anthropic | $0.00025 / $0.00125 | Summarization, QA, Wikipedia, weather |
| `QUALITY` | GPT-4o-mini | OpenAI | $0.00015 / $0.00060 | Code generation, creative writing |
| `POWER` | Claude Sonnet 4.6 | Anthropic | $0.00300 / $0.01500 | Deep reasoning, analysis |

The router automatically downgrades tier selection when session budget runs low, and forces `ULTRA_CHEAP` when budget is critical.

---

## ✨ Key Features

- **Multi-agent tool suite** — Web search (Tavily), Wikipedia, calculator, datetime, live weather (OpenWeatherMap), each dispatched based on classified task type
- **Query rewriting with user control** — vague queries get rewritten for clarity via Groq before hitting the router; users choose Auto / Always Original / Ask Me Each Time in Settings
- **Response streaming** — real-time token-by-token display in the Streamlit UI
- **Persistent memory** — every session and message is saved to SQLite (`memory/store.py`), browsable in the History page with per-session analytics
- **Session analytics dashboard** — cost, latency, tier distribution, cache hit rate, and token usage charts, all live-updating
- **CSV export** — full session report (Analytics page) or per-session history export, ready for portfolio demos or cost audits
- **Eval harness** — automated test suite scoring task-type accuracy, tier accuracy, and cost/latency across a fixed query set

---

## 🛠️ Tech Stack

- **Orchestration:** LangGraph, LangChain, LangSmith
- **LLM Providers:** Anthropic (Claude Haiku / Sonnet), OpenAI (GPT-4o-mini), Groq (Llama 3.1 8B)
- **Semantic Cache:** sentence-transformers (`all-MiniLM-L6-v2`) + cosine similarity
- **Persistence:** SQLite via LangGraph's `SqliteSaver` (graph checkpointing) + a custom `ConversationStore` (conversation history)
- **Tools:** Tavily (web search), Wikipedia API, OpenWeatherMap
- **UI:** Streamlit (multi-page), Plotly
- **Config:** pydantic-settings
- **Linting:** Ruff + Black

---

## 📁 Project Structure

```
TieredFlow/
├── config/           # Settings, constants, model metadata
├── core/             # Graph assembly, state schema
├── nodes/            # All LangGraph nodes (guardrail, cache, router, LLM, HITL, rewriter)
├── providers/        # Anthropic / OpenAI / Groq adapters (Strategy pattern)
├── cache/            # Semantic cache implementation
├── tools/            # Web search, Wikipedia, calculator, datetime, weather
├── memory/           # Persistent SQLite conversation store
├── eval/             # Evaluation harness + results
├── ui/               # Multi-page Streamlit app
├── tests/            # Test suite
├── utils/            # CSV export helpers
└── main.py           # CLI entry point
```

---

## 🚀 Setup

### Prerequisites
- Python 3.11+
- API keys: Anthropic, OpenAI, Groq, Tavily, OpenWeatherMap (free tier fine for all)

### Local installation

```bash
git clone https://github.com/<your-username>/TieredFlow---A-Cost-Latency-Optimizing-Multi-Agent-Orchestrator.git
cd TieredFlow---A-Cost-Latency-Optimizing-Multi-Agent-Orchestrator

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Fill in your API keys in .env
```

### Run via CLI

```bash
python main.py "who invented the light bulb"
```

### Run the Streamlit UI

```bash
streamlit run ui/app.py
```

### Run the eval harness

```bash
python eval/harness.py
```

---

## ☁️ Deployment (Streamlit Community Cloud)

TieredFlow is deployed on **Streamlit Community Cloud** — free, purpose-built for Streamlit apps, and zero-config beyond secrets.

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **"New app"** → select the repo → branch `main` → main file path `ui/app.py`.
4. Under **Advanced settings**, paste secrets in TOML format:
   ```toml
   ANTHROPIC_API_KEY = "..."
   OPENAI_API_KEY = "..."
   GROQ_API_KEY = "..."
   TAVILY_API_KEY = "..."
   OPENWEATHERMAP_API_KEY = "..."
   LANGCHAIN_API_KEY = "..."
   LANGCHAIN_TRACING_V2 = "true"
   LANGCHAIN_PROJECT = "tieredflow"
   ```
5. Click **Deploy**.

`config/settings.py` transparently loads from `st.secrets` on Streamlit Cloud and falls back to a local `.env` file otherwise — the same codebase runs unmodified in both environments.

**Two real deployment issues hit and fixed along the way** (both are good "what would you do differently in production" interview talking points):

- **Multipage import resolution** — Streamlit Cloud executes each page in `ui/pages/` with its own module search path, which doesn't automatically include the project root. Every page now inserts the project root into `sys.path` as the very first statement (before any other import), so `config`, `core`, `nodes`, etc. resolve correctly regardless of which page loads first.
- **Read-only app source mount** — the cloned repo directory on Streamlit Cloud is not reliably writable, which caused SQLite's `CREATE TABLE` to silently fail (the connection succeeded, but the schema never persisted, surfacing later as `OperationalError: no such table`). Both the LangGraph `SqliteSaver` checkpoint DB and the `ConversationStore` DB now write to the OS temp directory (`tempfile.gettempdir()`) instead of the project root, which is guaranteed writable across environments.

> **Known limitation:** the OS temp directory (like most PaaS free-tier filesystems) is ephemeral — session history and semantic cache reset on app reboot/redeploy. This is an accepted, explainable trade-off for a portfolio demo; a production deployment would instead point `DB_PATH` at a managed Postgres instance or a mounted persistent volume.

---

## 📊 Evaluation Results

Run via `eval/harness.py` against a 9-case benchmark spanning all task types:

| Metric | Result |
|---|---|
| Task type classification accuracy | 100% |
| Tier selection accuracy | 100% |
| Cache hit rate | 11.1% (1 intentional repeat query) |
| Avg cost per query | ~$0.00058 |
| Avg latency | varies by tier (300ms–7s) |

Full breakdown available in [`eval/results/eval_results.csv`](eval/results/eval_results.csv).

---

## 🧩 Key Architectural Decisions

- **Classifier runs before cache lookup** — this lets `REALTIME_QA` queries (news, prices, "today") bypass the semantic cache entirely, since time-sensitive answers should never be served stale.
- **Query rewriter runs after cache lookup, before router** — rewriting the query *before* checking cache would silently degrade cache hit rates, since a rewritten query rarely matches previously cached raw queries. Rewriting only happens right before a real LLM call would occur, so no compute is wasted rewriting queries that end up cache-served anyway.
- **Confidence scores are stored inside `call_log` entries, not as a top-level state field** — LangGraph's `SqliteSaver` was silently dropping `Optional` fields initialized to `None` on state re-assembly after checkpointing. Storing scores inside the `call_log` list (which merges via list-append, not scalar overwrite) sidesteps that entirely.
- **Wikipedia tool falls back to combined web search + LLM knowledge, not either alone** — when Wikipedia has no dedicated article, blindly trusting a thin web search result or letting the model guess from memory both risk wrong answers. Combining both lets the model cross-check search snippets against what it already knows.
- **Three independent HITL interrupt points** (cache-serve decision, tier override, rewrite choice) are implemented as first-class LangGraph interrupts rather than UI-only prompts — meaning the same HITL flow works identically whether invoked from the CLI or the Streamlit UI.
- **pydantic-settings over `python-dotenv` + `os.environ`** — gives type-safe, validated config loading with clear errors on missing keys, rather than silent `None`s surfacing deep in a provider call.
- **Semantic cache is keyed on the original query, never the rewritten one** — the query rewriter mutates `state["user_query"]` for the LLM call, but caching under that rewritten text would mean the same original query never matches itself on a repeat ask (two independent rewrites of the same vague query rarely produce identical text). Cache `store()` calls always use `original_query`, keeping lookup and storage aligned on what the user actually typed.

---

## 📸 Screenshots

**🔗 Live demo:** [tieredflow---a-cost-latency-optimizing-multi-agent-orchestrator.streamlit.app]((https://tieredflow.streamlit.app))

| | |
|---|---|
| **Landing page** — quick nav to all four pages | **Chat — empty state** with example prompts |
| ![Landing](docs/screenshots/01_landing_page.png) | ![Chat empty](docs/screenshots/04_chat_empty.png) |
| **HITL — query rewrite decision** — user chooses original vs. rewritten query before any cost is incurred | **Chat — fresh response** with full routing transparency |
| ![Rewrite decision](docs/screenshots/05_rewrite_decision.png) | ![Chat response](docs/screenshots/06_chat_response.png) |
| **Analytics dashboard** — cost, tier distribution, latency, and cache hit rate, all live | **History** — per-session breakdown with full conversation replay |
| ![Analytics](docs/screenshots/07_analytics.png) | ![History](docs/screenshots/08_history.png) |
| **Settings — cache thresholds** | **Settings — model tiers & query rewriting mode** |
| ![Settings cache](docs/screenshots/02_settings_cache.png) | ![Settings tiers](docs/screenshots/03_settings_tiers.png) |

---
