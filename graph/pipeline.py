"""
LangGraph Orchestration — Hotel GM Intelligence 3.0
──────────────────────────────────────────────────────
Replaces: agents/orchestrator.py, revenue_agent.py, ops_agent.py,
          reputation_agent.py, payroll_agent.py  (CrewAI, v2.0)

"Agents reason; Services retrieve; Metrics compute." — unchanged from v2.0.
What changed is HOW the reasoning step is wired, and how anomalies are found:

  1. No autonomous tool-selection loops. Each domain node does one
     deterministic fetch (tools/*.py, untouched logic) then ONE LLM call
     that turns the JSON into narrative analysis.
  2. Anomaly detection is now a deterministic rule engine against
     config.py's existing thresholds, not something we hope the LLM
     notices. The LLM describes anomalies we already found in code; it
     doesn't decide whether they exist.
  3. The LLM is an open-weight model served over Groq's free API — no
     local weights, no GPU, no RAM pressure on Streamlit Cloud.
  4. Chat mode is a 1-shot JSON router + fetch + answer, not a ReAct
     tool-calling agent loop — far more reliable on smaller/free models.
"""

from __future__ import annotations
from typing import TypedDict
from datetime import datetime
import json

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

from tools.pms_tools import get_occupancy_forecast_analysis, get_arrivals_analysis, get_booking_pace_analysis
from tools.rms_tools import get_comp_set_analysis, get_channel_mix_analysis
from tools.review_tools import get_review_analysis
from tools.payroll_tools import get_payroll_analysis
from memory.hotel_memory import HotelMemory
from config import (
    HOTEL_NAME, GROQ_API_KEY, GROQ_MODEL_MAIN, GROQ_MODEL_FAST,
    OCCUPANCY_LOW_THRESHOLD, REVIEW_SCORE_LOW, COMP_SET_RATE_GAP,
)

memory = HotelMemory()
llm = ChatGroq(model=GROQ_MODEL_MAIN, temperature=0.1, api_key=GROQ_API_KEY)
llm_fast = ChatGroq(model=GROQ_MODEL_FAST, temperature=0.1, api_key=GROQ_API_KEY)


# ─── 1. Shared graph state ──────────────────────────────────────────────────
class BriefingState(TypedDict, total=False):
    revenue_data: dict
    ops_data: dict
    reputation_data: dict
    payroll_data: dict
    revenue_analysis: str
    ops_analysis: str
    reputation_analysis: str
    payroll_analysis: str
    anomalies: list
    briefing: str


def _reason(system_prompt: str, payload: dict, task: str) -> str:
    """One deterministic LLM call: data in, narrative analysis out."""
    resp = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{task}\n\nDATA:\n{json.dumps(payload, indent=2, default=str)}"},
    ])
    return resp.content


# ─── 2. Domain nodes (fetch -> analyze) ────────────────────────────────────
def revenue_node(state: BriefingState) -> dict:
    data = {
        "occupancy": get_occupancy_forecast_analysis(30),
        "comp_set": get_comp_set_analysis(14),
        "pace": get_booking_pace_analysis(14),
        "channel_mix": get_channel_mix_analysis(),
    }
    analysis = _reason(
        "You are a hotel revenue manager. Think in RevPAR = ADR x Occupancy.",
        data,
        "Identify soft dates, comp-set positioning, booking pace, and 2 "
        "specific rate actions with dates and $ impact.",
    )
    return {"revenue_data": data, "revenue_analysis": analysis}


def ops_node(state: BriefingState) -> dict:
    data = get_arrivals_analysis()
    analysis = _reason(
        "You are a hotel front-of-house operations manager.",
        data,
        "Flag VIPs needing personal welcome, special-request prep, and any OTA margin warning.",
    )
    return {"ops_data": data, "ops_analysis": analysis}


def reputation_node(state: BriefingState) -> dict:
    data = get_review_analysis(30)
    analysis = _reason(
        "You are a guest experience director.",
        data,
        "Name the top complaint theme, the worst department, and one operational fix.",
    )
    return {"reputation_data": data, "reputation_analysis": analysis}


def payroll_node(state: BriefingState) -> dict:
    data = get_payroll_analysis()
    analysis = _reason(
        "You are a hotel financial controller focused on protecting GOP.",
        data,
        "Name the worst-offending department, its $ overrun, and 2 corrective actions.",
    )
    return {"payroll_data": data, "payroll_analysis": analysis}


# ─── 3. Deterministic anomaly rule engine ──────────────────────────────────
def detect_anomalies(state: BriefingState) -> list[tuple[str, str, str]]:
    """
    Runs config.py's thresholds against the already-fetched data.
    Returns (type, description, severity) tuples. This is code, not an
    LLM guess — the LLM's job downstream is only to explain these, not
    to decide whether they're real.
    """
    found = []

    occ = state.get("revenue_data", {}).get("occupancy", {})
    if occ and occ.get("avg_occupancy_pct", 100) < OCCUPANCY_LOW_THRESHOLD:
        gap = OCCUPANCY_LOW_THRESHOLD - occ["avg_occupancy_pct"]
        found.append((
            "occupancy",
            f"Average 30-day occupancy is {occ['avg_occupancy_pct']}%, "
            f"below the {OCCUPANCY_LOW_THRESHOLD}% threshold, with "
            f"{occ.get('soft_dates_count', 0)} soft dates flagged.",
            "high" if gap > 15 else "medium",
        ))

    comp = state.get("revenue_data", {}).get("comp_set", {})
    if comp and comp.get("underpriced_dates_count", 0) > 0:
        found.append((
            "pricing",
            f"{comp['underpriced_dates_count']} upcoming dates are "
            f"underpriced vs comp set by more than ${COMP_SET_RATE_GAP}.",
            "medium",
        ))

    for dept in state.get("payroll_data", {}).get("flagged_departments", []):
        found.append((
            "payroll",
            f"{dept['department']} payroll is {dept['variance_pct']}% over budget.",
            "high" if dept["variance_pct"] > 20 else "medium",
        ))

    rep = state.get("reputation_data", {})
    if rep and rep.get("avg_score", 5) < REVIEW_SCORE_LOW:
        found.append((
            "reputation",
            f"Average guest score is {rep['avg_score']}, below the "
            f"{REVIEW_SCORE_LOW} threshold. Worst department: "
            f"{rep.get('worst_department', 'N/A')}.",
            "high",
        ))

    ops = state.get("ops_data", {})
    if ops and ops.get("ota_warning"):
        found.append((
            "channel_mix",
            f"OTA bookings are {ops.get('ota_percentage')}% of today's "
            "arrivals, above the 60% margin-risk line.",
            "medium",
        ))

    return found


# ─── 4. Orchestrator node — anomaly scan + synthesis ───────────────────────
def synthesis_node(state: BriefingState) -> dict:
    anomalies = detect_anomalies(state)
    for a_type, description, severity in anomalies:
        memory.save_anomaly(a_type, description, severity)

    combined = {
        "revenue": state.get("revenue_analysis", ""),
        "operations": state.get("ops_analysis", ""),
        "reputation": state.get("reputation_analysis", ""),
        "payroll": state.get("payroll_analysis", ""),
        "detected_anomalies": [
            {"type": t, "description": d, "severity": s} for t, d, s in anomalies
        ],
    }
    briefing = _reason(
        f"You are the AI Chief of Staff for the GM of {HOTEL_NAME}. "
        "Never pad. Every bullet needs a number, a date, or a $ amount. "
        "The detected_anomalies list is already verified — describe them, "
        "don't second-guess whether they're real.",
        combined,
        f"Today is {datetime.today():%A, %B %d %Y}. Write the GM Morning "
        "Briefing: overall health score (GREEN/AMBER/RED), top 5 ranked "
        "actions, one snapshot per department, and an anomalies list. "
        "Markdown, tight bullets, no filler.",
    )
    return {"briefing": briefing, "anomalies": anomalies}


# ─── 5. Wire the graph: fan-out to 4 domains, fan-in to synthesis ─────────
def build_briefing_graph():
    graph = StateGraph(BriefingState)
    graph.add_node("revenue", revenue_node)
    graph.add_node("ops", ops_node)
    graph.add_node("reputation", reputation_node)
    graph.add_node("payroll", payroll_node)
    graph.add_node("synthesis", synthesis_node)

    for domain in ("revenue", "ops", "reputation", "payroll"):
        graph.add_edge(START, domain)
        graph.add_edge(domain, "synthesis")

    graph.add_edge("synthesis", END)
    return graph.compile()


def run_full_briefing() -> str:
    """Drop-in replacement for the old CrewAI run_full_briefing()."""
    app = build_briefing_graph()
    result = app.invoke({})
    briefing = result["briefing"]
    memory.save_briefing(briefing)
    return briefing


# ─── 6. Chat mode — 1-shot router + fetch + answer, NOT a ReAct loop ──────
FETCHERS = {
    "revenue": lambda: {
        "occupancy": get_occupancy_forecast_analysis(30),
        "comp_set": get_comp_set_analysis(14),
        "pace": get_booking_pace_analysis(14),
    },
    "ops": get_arrivals_analysis,
    "reputation": get_review_analysis,
    "payroll": get_payroll_analysis,
}


def run_gm_chat(question: str, briefing_context: str = "") -> str:
    """Drop-in replacement for the old CrewAI run_gm_chat()."""
    memory.save_chat("gm", question)
    history = memory.get_chat_history(5)
    history_text = "\n".join(f"{h['role'].upper()}: {h['content']}" for h in history) or "No previous conversation."

    route = llm_fast.invoke([
        {"role": "system", "content": (
            "Classify which hotel data domains are needed to answer the "
            "question. Reply ONLY with JSON like {\"domains\": [\"revenue\"]} "
            "using any of: revenue, ops, reputation, payroll."
        )},
        {"role": "user", "content": question},
    ])
    try:
        domains = json.loads(route.content).get("domains", ["revenue"])
    except (json.JSONDecodeError, AttributeError, TypeError):
        domains = ["revenue"]

    context = {d: FETCHERS[d]() for d in domains if d in FETCHERS}
    answer = _reason(
        f"You are the AI assistant for the GM of {HOTEL_NAME}.\n\n"
        f"Today's briefing context:\n{briefing_context[:2000]}\n\n"
        f"Recent conversation:\n{history_text}",
        context,
        f"Answer precisely with numbers and dates, then give 1 action item.\n\nQuestion: {question}",
    )
    memory.save_chat("agent", answer)
    return answer
