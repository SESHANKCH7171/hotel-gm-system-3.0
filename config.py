import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# ─── Hotel Identity ─────────────────────────────────────────────────────────
HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Plaza Hotel")
HOTEL_ID = os.getenv("HOTEL_ID", "hotel_001")

# ─── API Keys (with Streamlit Cloud fallback) ────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass

# ─── LLM Config (open-weight models served over Groq's free API) ───────────
# GROQ_MODEL_MAIN handles domain analysis + synthesis (quality matters most).
# GROQ_MODEL_FAST handles the chat-mode router (cheap 1-shot classification).
GROQ_MODEL_MAIN = os.getenv("GROQ_MODEL_MAIN", "openai/gpt-oss-20b")
GROQ_MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "openai/gpt-oss-20b")

# ─── Anomaly Detection Thresholds ────────────────────────────────────────────
# These now drive a deterministic rule engine (graph/pipeline.py) instead of
# being descriptive text inside an LLM prompt.
OCCUPANCY_LOW_THRESHOLD = 60       # % — flag if below this
ADR_DROP_THRESHOLD = 15            # % drop vs last week — flag
REVIEW_SCORE_LOW = 3.5             # flag if avg below this
PAYROLL_SPIKE_THRESHOLD = 10       # % spike vs forecast — flag
COMP_SET_RATE_GAP = 20             # $ gap vs comp set — flag

# ─── Memory ──────────────────────────────────────────────────────────────────
SQLITE_DB_PATH = "./memory/hotel_memory.db"
