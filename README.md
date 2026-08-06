# 🏨 Hotel GM Intelligence Agent 3.0

> **Multi-agent AI system for hotel General Managers** — Revenue, Operations, Reputation & Payroll intelligence in one dashboard with Real-Time WebRTC Voice Copilot.

**"Agents reason; Services retrieve; Metrics compute."** — same philosophy as v1.0/v2.0. What changed in 3.0 is the orchestration engine, the model, and real-time voice interactions.

## What changed from v2.0

| | v2.0 | v3.0 |
|---|---|---|
| Orchestration | CrewAI (`Agent`/`Task`/`Crew`, autonomous tool loops) | LangGraph (explicit fan-out/fan-in state graph) |
| LLM | Google Gemini 2.0 / 2.5 Flash | Open-weight models (Llama 3.3 70B / 3.1 8B) via Groq |
| Voice Copilot | N/A | Real-Time LiveKit WebRTC Voice Agent (Silero VAD + ElevenLabs + Groq LPU) |
| Memory | ChromaDB (vector search) | SQLite (plain recency queries) |
| Anomaly detection | Implicit, left to the LLM's judgment | Deterministic rule engine against `config.py` thresholds |

The CrewAI agents never actually delegated or chose between tools — each one always ran the same fixed tool once, then wrote a report. That's a linear pipeline, not agentic behavior, so v3.0 writes it as what it is: a graph.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐      ┌─────────────────────────────┐
│              GM Dashboard (Streamlit)            │      │  🎙️ WebRTC Voice Copilot   │
│  [Daily Brief] [Chat] [Live Data] [Memory]      │      │     (LiveKit + Voice Agent) │
└──────────────────┬──────────────────────────────┘      └──────────────┬──────────────┘
                   │                                                    │
                   └──────────────────┐           ┌─────────────────────┘
                                      ▼           ▼
                            ┌──────────────────┐
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

### Real-Time Voice Copilot (LiveKit WebRTC)
v3.0 adds a low-latency WebRTC Voice Agent (`voice_agent.py`) using Silero VAD, ElevenLabs TTS, and Groq's high-speed LPU infrastructure. The agent directly triggers the LangGraph `query_hotel_systems` function tool when the General Manager speaks data queries.

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
├── app.py                      # Streamlit UI (Dashboard + Secure Voice Portal Launcher)
├── voice_agent.py              # Real-time LiveKit WebRTC Voice Copilot worker
├── config.py                   # Centralized configuration (Groq + SQLite + LiveKit)
├── requirements.txt            # Python dependencies (LangGraph, LiveKit, Streamlit, etc.)
├── .env.example                # Copy to .env and fill in credentials
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
# Edit .env: add your GROQ_API_KEY and LiveKit keys (from cloud.livekit.io)

# 1. Run the Voice Agent (Worker)
python voice_agent.py start

# 2. Run the Streamlit Dashboard (In a separate terminal)
streamlit run app.py
```

### Streamlit Cloud Deployment

1. Push to GitHub
2. Connect the repo on [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in the dashboard:
   ```toml
   GROQ_API_KEY = "your-key-here"
   LIVEKIT_URL = "wss://your-project.livekit.cloud"
   LIVEKIT_API_KEY = "your-key"
   LIVEKIT_API_SECRET = "your-secret"
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
- **Voice Engine:** LiveKit WebRTC + Silero VAD + ElevenLabs TTS
- **Memory:** SQLite (persistent, recency-based)
- **UI:** Streamlit + Plotly
- **Data:** Faker + NumPy (synthetic mock generators)

## 👤 Built By

**Seshank Chinnapotula**

