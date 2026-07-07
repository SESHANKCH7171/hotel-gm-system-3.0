# 🏨 Hotel GM Intelligence Agent 3.0

> **Multi-agent AI system for hotel General Managers** — Revenue, Operations, Reputation & Payroll intelligence in one dashboard.

**"Agents reason; Services retrieve; Metrics compute."** — same philosophy as v1.0/v2.0. What changed in 3.0 is the orchestration engine and the model.

## What changed from v2.0

| | v2.0 | v3.0 |
|---|---|---|
| Orchestration | CrewAI (`Agent`/`Task`/`Crew`, autonomous tool loops) | LangGraph (explicit fan-out/fan-in state graph) |
| LLM | Google Gemini 2.0 Flash | Open-weight models (Llama 3.3 70B) via Groq's free API |
| Memory | ChromaDB (vector search) | SQLite (plain recency queries) |
| Anomaly detection | Implicit, left to the LLM's judgment | Deterministic rule engine against `config.py` thresholds |

The CrewAI agents never actually delegated or chose between tools — each one always ran the same fixed tool once, then wrote a report. That's a linear pipeline, not agentic behavior, so v3.0 writes it as what it is: a graph.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              GM Dashboard (Streamlit)            │
│  [Daily Brief] [Chat] [Live Data] [Memory]      │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  LangGraph pipeline │  fan-out → domain nodes → fan-in → synthesis
         └──┬──┬──┬──┬────────┘
            │  │  │  │
    ┌───────┘  │  │  └──────────┐
    ▼          ▼  ▼             ▼
┌───────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│Revenue│ │Ops   │ │Repute  │ │Payroll   │
│node   │ │node  │ │node    │ │node      │
└───┬───┘ └──┬───┘ └───┬────┘ └────┬─────┘
    │        │          │           │
    ▼        ▼          ▼           ▼
  PMS/RMS  Arrivals   Reviews    Payroll
  tools    tools      tools      tools
```

Each domain node: one deterministic Python fetch (`tools/*.py`, logic unchanged from v2.0) → one LLM call that turns the JSON into narrative analysis. No tool-selection reasoning, no `max_iter`, no `allow_delegation` — that uncertainty is resolved in code, not left to the model.

### Why no ChromaDB in 3.0?

Two of v2.0's three ChromaDB use cases were never actually semantic search — "load the last briefing" and "recent chat history" are both `ORDER BY date DESC`, not similarity search. The one genuinely semantic use case, anomaly pattern-matching, is now a deterministic rule engine (`graph/pipeline.py::detect_anomalies`) checked against the same thresholds `config.py` always defined. This removes chromadb + onnxruntime + an embedding model from the dependency tree, which matters on Streamlit Community Cloud's 1GB RAM ceiling.

### Why an open-weight model over Groq instead of local inference?

Streamlit Community Cloud's free tier is capped at 1GB RAM. `transformers`/`torch` overhead alone typically exceeds that before a single weight loads, regardless of model size. Calling an open-weight model over Groq's free API keeps zero LLM weights in the Streamlit process while still using open-source models (Llama 3.3 70B for reasoning, Llama 3.1 8B for the chat-mode router), not a proprietary API.

## 🧮 Hotel KPI Definitions

| KPI | Formula | Purpose |
|-----|---------|---------|
| **Occupancy** | Rooms Sold / Rooms Available | Demand indicator |
| **ADR** | Room Revenue / Rooms Sold | Price indicator |
| **RevPAR** | Room Revenue / Rooms Available = ADR × Occupancy | Anchor metric (combines both) |
| **GOP** | Revenue - Operating Expenses | Profitability |

## 📁 Project Structure

```
hotel-gm-system-3.0/
├── app.py                      # Streamlit UI (4 pages) — unchanged from v2.0
├── config.py                   # Centralized configuration (Groq + SQLite)
├── requirements.txt
├── .env.example                # Copy to .env and fill in GROQ_API_KEY
├── Dockerfile
├── .streamlit/
│   └── config.toml             # Dark theme
├── graph/
│   └── pipeline.py             # LangGraph nodes, anomaly rule engine, chat router
├── tools/
│   ├── pms_tools.py            # PMS: occupancy, arrivals, pace
│   ├── rms_tools.py            # RMS: comp set, channel mix
│   ├── review_tools.py         # Reviews: multi-platform analysis
│   └── payroll_tools.py        # Payroll: budget vs actual
├── data/
│   └── mock_hotel_data.py      # Synthetic PMS/RMS/payroll/review data (Faker + NumPy)
└── memory/
    └── hotel_memory.py         # SQLite persistent memory
```

`data/mock_hotel_data.py` is 100% synthetic — Faker + NumPy generating pandas DataFrames in-process. There is no real PMS/RDBMS connection; that's by design for a demo, and swappable for a real adapter later.

## 🚀 Setup & Run

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env: add your GROQ_API_KEY (free, no card, at console.groq.com)

streamlit run app.py
```

### Streamlit Cloud Deployment

1. Push to GitHub
2. Connect the repo on [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in the dashboard:
   ```toml
   GROQ_API_KEY = "your-key-here"
   ```

## 🎯 Demo Queries

- "RevPAR dropped 12% over the last 7 days. Was it occupancy, ADR, cancellations, or channel mix?"
- "Which dates need pricing action?"
- "What is pickup vs last year?"
- "Which department is bleeding payroll?"
- "What's our worst-rated department in reviews?"

## 🔧 Tech Stack

- **Orchestration:** LangGraph (fan-out/fan-in state graph)
- **LLM:** Open-weight models via Groq's free API (Llama 3.3 70B / Llama 3.1 8B)
- **Memory:** SQLite (persistent, recency-based)
- **UI:** Streamlit + Plotly
- **Data:** Faker + NumPy (synthetic mock generators)

## 👤 Built By

**Seshank Chinnapotula**
