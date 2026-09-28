import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import os
import uuid
from livekit import api
import streamlit.components.v1 as components
from graph.pipeline import run_full_briefing, run_gm_chat
from dotenv import load_dotenv

load_dotenv()

from data.mock_hotel_data import (
    get_occupancy_forecast,
    get_comp_set_rates,
    get_reviews,
    get_payroll_data,
    get_booking_pace,
    get_channel_mix,
)
from memory.hotel_memory import HotelMemory
from config import HOTEL_NAME


# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{HOTEL_NAME} — GM Intelligence",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── LiveKit WebRTC Token Generation ─────────────────────────────────────────
if "room_name" not in st.session_state:
    st.session_state.room_name = f"gm-room-{uuid.uuid4().hex[:8]}"

livekit_url = os.environ.get("LIVEKIT_URL", "")
livekit_key = os.environ.get("LIVEKIT_API_KEY", "")
livekit_secret = os.environ.get("LIVEKIT_API_SECRET", "")

if livekit_key and livekit_secret:
    token = api.AccessToken(livekit_key, livekit_secret) \
        .with_identity("hotel-gm") \
        .with_name("General Manager") \
        .with_grants(api.VideoGrants(room_join=True, room=st.session_state.room_name)) \
        .to_jwt()

    livekit_html = f"""
    <script type="module" src="https://cdn.jsdelivr.net/npm/@livekit/agent-embed@latest/dist/widget.js"></script>
    <livekit-agent-embed
      url="{livekit_url}"
      token="{token}"
      theme="dark"
      style="height: 100%; width: 100%;">
    </livekit-agent-embed>
    """
else:
    livekit_html = None

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main { background-color: #0f1117; font-family: 'Inter', sans-serif; }

    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(79, 142, 247, 0.15);
    }

    .alert-red {
        background: #2d1b1b;
        border-left: 4px solid #ff4444;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 6px 0;
        font-size: 0.9rem;
    }
    .alert-amber {
        background: #2d2510;
        border-left: 4px solid #ffaa00;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 6px 0;
        font-size: 0.9rem;
    }
    .alert-green {
        background: #112d1e;
        border-left: 4px solid #00cc66;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 6px 0;
        font-size: 0.9rem;
    }

    .briefing-box {
        background: #1a1d2e;
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 24px;
        font-family: 'Inter', sans-serif;
        line-height: 1.8;
        font-size: 0.95rem;
    }

    .stButton > button {
        background: linear-gradient(135deg, #4f8ef7, #7c4dff) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(79, 142, 247, 0.3) !important;
    }

    .example-btn > button {
        background: linear-gradient(135deg, #1e2130, #252840) !important;
        border: 1px solid #3d4260 !important;
        font-size: 0.85rem !important;
    }

    h1, h2, h3 { font-family: 'Inter', sans-serif !important; }

    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #fafafa;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State Init ─────────────────────────────────────────────────────
if "briefing" not in st.session_state:
    st.session_state.briefing = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "briefing_run" not in st.session_state:
    st.session_state.briefing_run = False

memory = HotelMemory()


# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="sidebar-title">🏨 {HOTEL_NAME}</div>', unsafe_allow_html=True)
    st.caption("GM Intelligence Dashboard v3.0")
    st.divider()

    # Date and Time
    st.markdown(f"**📅 Today:** {datetime.today().strftime('%A, %d %B %Y')}")
    st.markdown(f"**🕐 Time:** {datetime.now().strftime('%H:%M')} hrs")
    st.divider()

    # Navigation Menu (Placed prominently at the top)
    st.markdown("**📌 Navigation**")
    page = st.radio(
        "Navigate",
        ["🌅 Morning Briefing", "💬 Ask the Agent", "📊 Live Data", "🧠 Memory Log"],
        label_visibility="collapsed",
    )

    st.divider()

    # Memory stats
    stats = memory.get_stats()
    st.markdown("**📊 Memory Stats**")
    st.caption(f"Briefings: {stats['total_briefings']} | Anomalies: {stats['total_anomalies']} | Chats: {stats['total_chat_messages']}")

    st.divider()

    # Voice Copilot Embed (Placed at the bottom for smooth expansion)
    # ─── VOICE AGENT SECURE PORTAL ───────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="sidebar-title">🎙️ Voice Copilot</div>', unsafe_allow_html=True)
    st.caption("Real-Time WebRTC Interface")
    
    if livekit_html: # We still use this to check if the token generated successfully
        st.success("✅ Voice Server Online")
        st.markdown(
            "<span style='font-size: 0.85rem; color: #a0aec0;'>"
            "For executive privacy and to bypass browser iframe sandboxing, microphone access is routed through the secure portal."
            "</span>", 
            unsafe_allow_html=True
        )
        
        # Display the credentials so the GM can copy them
        with st.expander("🔑 View Connection Credentials"):
            st.text("Copy these to connect:")
            st.code(f"URL: {livekit_url}", language="text")
            st.code(f"Token: {token}", language="text")
            
        # Button to open the Playground in a new tab
        st.link_button("Launch Secure Voice Portal ↗", "https://agents-playground.livekit.io/", use_container_width=True)
    else:
        st.warning("⚠️ LiveKit keys missing in .env. Voice Agent disabled.")

    st.divider()
    st.caption("Powered by LangGraph + OpenAI/gpt-oss-20b (Groq)")
    st.caption("Built by Seshank Chinnapotula")
    st.caption("*Agents reason; Services retrieve; Metrics compute.*")

# ═══════════════════════════════════════════════════════════════
# PAGE 1 — MORNING BRIEFING
# ═══════════════════════════════════════════════════════════════
if page == "🌅 Morning Briefing":
    st.title("🌅 GM Morning Briefing")
    st.caption("AI-generated intelligence from all hotel systems — Revenue, Operations, Reputation & Payroll")
    st.divider()

    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        run_btn = st.button("⚡ Generate Today's Briefing", use_container_width=True)
    with col2:
        if st.button("📋 Load Last Briefing", use_container_width=True):
            past = memory.get_past_briefings(1)
            if past:
                st.session_state.briefing = past[0]
                st.session_state.briefing_run = True
            else:
                st.warning("No past briefings found. Generate one first!")
    with col3:
        if st.button("🔄 Clear & Reset", use_container_width=True):
            st.session_state.briefing = None
            st.session_state.briefing_run = False
            st.rerun()

    # Generate briefing
    if run_btn:
        with st.spinner("🤖 Agents are analysing all hotel systems... This takes ~60-90 seconds."):
            try:
                briefing = run_full_briefing()
                st.session_state.briefing = briefing
                st.session_state.briefing_run = True
                st.success("✅ Briefing generated successfully!")
            except Exception as e:
                st.error(f"❌ Error running agents: {e}")

    # Display briefing
    if st.session_state.briefing_run and st.session_state.briefing:
        st.markdown("---")

        # Quick KPI cards from live data
        occ_df = get_occupancy_forecast(7)
        pay_df = get_payroll_data()
        rev_df = get_reviews(20)

        avg_occ = round(occ_df['occupancy_pct'].mean(), 1)
        avg_adr = round(occ_df['adr'].mean(), 2)
        avg_revpar = round(occ_df['revpar'].mean(), 2)
        avg_score = round(rev_df['score'].mean(), 2)
        total_var = round(
            ((pay_df['actual'].sum() - pay_df['budget'].sum()) / pay_df['budget'].sum()) * 100, 1
        )

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric(
            "7-Day Avg Occupancy",
            f"{avg_occ}%",
            delta=f"{round(avg_occ - 65, 1)}% vs 65% target",
        )
        k2.metric("Avg ADR", f"${avg_adr}")
        k3.metric("Avg RevPAR", f"${avg_revpar}")
        k4.metric(
            "Guest Score",
            f"{avg_score}/5",
            delta=f"{'Above' if avg_score >= 4.0 else 'Below'} 4.0 target",
            delta_color="normal" if avg_score >= 4.0 else "inverse",
        )
        k5.metric(
            "Payroll vs Budget",
            f"{total_var:+}%",
            delta_color="inverse" if total_var > 5 else "normal",
        )

        st.markdown("---")

        # Briefing output
        st.markdown("### 📋 Full GM Briefing Pack")
        with st.container(border=True):
            st.markdown(st.session_state.briefing)

        # Download button
        st.download_button(
            label="⬇️ Download Briefing as .txt",
            data=st.session_state.briefing,
            file_name=f"GM_Briefing_{datetime.today().strftime('%Y-%m-%d')}.txt",
            mime="text/plain",
        )


# ═══════════════════════════════════════════════════════════════
# PAGE 2 — ASK THE AGENT
# ═══════════════════════════════════════════════════════════════
elif page == "💬 Ask the Agent":
    st.title("💬 Ask Your GM Agent")
    st.caption("Ask anything about revenue, operations, guests, payroll — get data-backed answers instantly.")
    st.divider()

    # Example prompts
    st.markdown("**Try asking:**")
    ex1, ex2, ex3, ex4 = st.columns(4)

    examples = {
        ex1: "Which dates next month are underpriced vs competitors?",
        ex2: "Which department is over payroll budget?",
        ex3: "How many VIP guests arrive today?",
        ex4: "Why did RevPAR drop — was it occupancy, ADR, or both?",
    }

    for col, prompt_text in examples.items():
        with col:
            st.markdown(f"""
            <div class="metric-card" style="font-size:0.8rem; min-height:80px; display:flex; align-items:center; justify-content:center;">
                💡 {prompt_text}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Chat display
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask your GM Agent anything..."):
        # Show user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("🤖 Analysing hotel data..."):
                try:
                    briefing_ctx = st.session_state.briefing or ""
                    response = run_gm_chat(prompt, briefing_ctx)
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"❌ Error: {e}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})


# ═══════════════════════════════════════════════════════════════
# PAGE 3 — LIVE DATA DASHBOARD
# ═══════════════════════════════════════════════════════════════
elif page == "📊 Live Data":
    st.title("📊 Live Hotel Data Dashboard")
    st.caption("Real-time data from all hotel systems — updated on every page load")
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Occupancy & RevPAR",
        "🏷️ Comp Set Rates",
        "⭐ Guest Reviews",
        "💰 Payroll",
        "📊 Channel Mix",
    ])

    # ── Tab 1: Occupancy & RevPAR ──────────────────────────────────────────
    with tab1:
        occ_df = get_occupancy_forecast(30)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("30-Day Avg Occupancy", f"{round(occ_df['occupancy_pct'].mean(), 1)}%")
        c2.metric("30-Day Avg ADR", f"${round(occ_df['adr'].mean(), 2)}")
        c3.metric("30-Day Avg RevPAR", f"${round(occ_df['revpar'].mean(), 2)}")
        soft_count = len(occ_df[occ_df['occupancy_pct'] < 50])
        c4.metric("Soft Dates (<50%)", f"{soft_count} days", delta_color="inverse" if soft_count > 3 else "normal")

        st.markdown("---")

        # Occupancy chart
        fig_occ = go.Figure()
        fig_occ.add_trace(go.Scatter(
            x=occ_df['date'], y=occ_df['occupancy_pct'],
            mode='lines+markers', name='Occupancy %',
            line=dict(color='#4f8ef7', width=2),
            marker=dict(size=5),
        ))
        fig_occ.add_hline(y=60, line_dash="dash", line_color="#ffaa00",
                          annotation_text="60% Target")
        fig_occ.update_layout(
            title="30-Day Occupancy Forecast",
            template="plotly_dark",
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            height=400,
            xaxis_title="Date",
            yaxis_title="Occupancy %",
        )
        st.plotly_chart(fig_occ, use_container_width=True)

        # RevPAR chart
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=occ_df['date'], y=occ_df['revpar'],
            name='RevPAR',
            marker_color='#7c4dff',
        ))
        fig_rev.add_trace(go.Scatter(
            x=occ_df['date'], y=occ_df['adr'],
            mode='lines', name='ADR',
            line=dict(color='#00cc66', width=2),
        ))
        fig_rev.update_layout(
            title="RevPAR vs ADR (30 Days)",
            template="plotly_dark",
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            height=400,
            xaxis_title="Date",
            yaxis_title="$",
            barmode='overlay',
        )
        st.plotly_chart(fig_rev, use_container_width=True)

        # Data table
        with st.expander("📋 View Raw Occupancy Data"):
            st.dataframe(occ_df, use_container_width=True, hide_index=True)

    # ── Tab 2: Comp Set Rates ──────────────────────────────────────────────
    with tab2:
        comp_df = get_comp_set_rates(14)

        avg_gap = round(comp_df['gap'].mean(), 2)
        position = "UNDERPRICED 🔴" if avg_gap < -10 else "OVERPRICED 🟡" if avg_gap > 10 else "ALIGNED ✅"

        c1, c2 = st.columns(2)
        c1.metric("Avg Rate Gap vs Market", f"${avg_gap}")
        c2.metric("Market Position", position)

        st.markdown("---")

        # Rate comparison chart
        daily_avg = comp_df.groupby('date').agg({
            'our_rate': 'first',
            'comp_rate': 'mean',
        }).reset_index()

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(
            x=daily_avg['date'], y=daily_avg['our_rate'],
            mode='lines+markers', name='Our Rate',
            line=dict(color='#4f8ef7', width=3),
        ))
        fig_comp.add_trace(go.Scatter(
            x=daily_avg['date'], y=daily_avg['comp_rate'],
            mode='lines+markers', name='Comp Set Avg',
            line=dict(color='#ff6b6b', width=2, dash='dash'),
        ))
        fig_comp.update_layout(
            title="Our Rates vs Comp Set Average (14 Days)",
            template="plotly_dark",
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            height=400,
            xaxis_title="Date",
            yaxis_title="Rate ($)",
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # By competitor
        fig_by_comp = px.box(
            comp_df, x='competitor', y='gap',
            title="Rate Gap Distribution by Competitor",
            template="plotly_dark",
            color='competitor',
        )
        fig_by_comp.update_layout(
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig_by_comp, use_container_width=True)

    # ── Tab 3: Guest Reviews ──────────────────────────────────────────────
    with tab3:
        rev_df = get_reviews(30)

        avg_score = round(rev_df['score'].mean(), 2)
        status_color = "🔴" if avg_score < 3.0 else "🟡" if avg_score < 3.8 else "🟢"
        unresponded = len(rev_df[(rev_df['score'] <= 3) & (rev_df['responded'] == False)])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Guest Score", f"{avg_score}/5 {status_color}")
        c2.metric("Total Reviews", len(rev_df))
        c3.metric("Unresponded Negatives", unresponded, delta_color="inverse")
        c4.metric("Response Rate", f"{round(rev_df['responded'].mean() * 100, 1)}%")

        st.markdown("---")

        col_left, col_right = st.columns(2)

        with col_left:
            # Score distribution
            fig_scores = px.histogram(
                rev_df, x='score', nbins=5,
                title="Review Score Distribution",
                template="plotly_dark",
                color_discrete_sequence=['#7c4dff'],
            )
            fig_scores.update_layout(
                paper_bgcolor="#0f1117",
                plot_bgcolor="#1a1d2e",
                height=350,
                xaxis_title="Score",
                yaxis_title="Count",
            )
            st.plotly_chart(fig_scores, use_container_width=True)

        with col_right:
            # Department scores
            dept_scores = rev_df.groupby('department')['score'].mean().sort_values().reset_index()
            fig_dept = px.bar(
                dept_scores, x='score', y='department',
                orientation='h', title="Average Score by Department",
                template="plotly_dark",
                color='score',
                color_continuous_scale=['#ff4444', '#ffaa00', '#00cc66'],
            )
            fig_dept.update_layout(
                paper_bgcolor="#0f1117",
                plot_bgcolor="#1a1d2e",
                height=350,
            )
            st.plotly_chart(fig_dept, use_container_width=True)

        # Platform breakdown
        fig_platform = px.pie(
            rev_df, names='platform',
            title="Reviews by Platform",
            template="plotly_dark",
            hole=0.4,
            color_discrete_sequence=['#4f8ef7', '#7c4dff', '#00cc66'],
        )
        fig_platform.update_layout(
            paper_bgcolor="#0f1117",
            height=350,
        )
        st.plotly_chart(fig_platform, use_container_width=True)

        # Urgent reviews
        urgent = rev_df[(rev_df['score'] <= 2) & (rev_df['responded'] == False)]
        if not urgent.empty:
            st.markdown("### 🚨 Urgent Unresponded Reviews")
            for _, row in urgent.iterrows():
                st.markdown(
                    f'<div class="alert-red">'
                    f'<strong>{row["platform"]}</strong> — ⭐ {row["score"]}/5 — {row["date"]}<br>'
                    f'"{row["text"]}"'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Tab 4: Payroll ─────────────────────────────────────────────────────
    with tab4:
        pay_df = get_payroll_data()

        total_budget = pay_df['budget'].sum()
        total_actual = pay_df['actual'].sum()
        total_var = round(((total_actual - total_budget) / total_budget) * 100, 1)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Payroll Budget", f"${total_budget:,.0f}")
        c2.metric("Total Payroll Actual", f"${total_actual:,.0f}")
        c3.metric(
            "Variance",
            f"{total_var:+}%",
            delta=f"${round(total_actual - total_budget):,}",
            delta_color="inverse" if total_var > 5 else "normal",
        )

        st.markdown("---")

        # Payroll bar chart
        fig_pay = go.Figure()
        fig_pay.add_trace(go.Bar(
            x=pay_df['department'], y=pay_df['budget'],
            name='Budget', marker_color='#4f8ef7',
        ))
        fig_pay.add_trace(go.Bar(
            x=pay_df['department'], y=pay_df['actual'],
            name='Actual', marker_color='#ff6b6b',
        ))
        fig_pay.update_layout(
            title="Payroll: Budget vs Actual by Department",
            template="plotly_dark",
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            height=400,
            barmode='group',
            xaxis_title="Department",
            yaxis_title="$",
        )
        st.plotly_chart(fig_pay, use_container_width=True)

        # Variance chart
        colors = ['#ff4444' if v > 10 else '#ffaa00' if v > 5 else '#00cc66'
                  for v in pay_df['variance_pct']]
        fig_var = go.Figure(go.Bar(
            x=pay_df['department'],
            y=pay_df['variance_pct'],
            marker_color=colors,
            text=[f"{v:+}%" for v in pay_df['variance_pct']],
            textposition='outside',
        ))
        fig_var.update_layout(
            title="Payroll Variance % by Department",
            template="plotly_dark",
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            height=400,
            xaxis_title="Department",
            yaxis_title="Variance %",
        )
        fig_var.add_hline(y=10, line_dash="dash", line_color="#ff4444",
                          annotation_text="10% Threshold")
        st.plotly_chart(fig_var, use_container_width=True)

        # Flagged departments
        spikes = pay_df[pay_df['variance_pct'] > 10]
        if not spikes.empty:
            st.markdown("### 🚨 Departments Over Budget")
            for _, row in spikes.iterrows():
                overrun = round(row['actual'] - row['budget'], 2)
                st.markdown(
                    f'<div class="alert-red">'
                    f'<strong>{row["department"]}</strong> — '
                    f'{row["variance_pct"]:+}% over budget — '
                    f'${overrun:,.0f} overrun'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Tab 5: Channel Mix ─────────────────────────────────────────────────
    with tab5:
        chan_df = get_channel_mix()

        total_bookings = chan_df['bookings'].sum()
        ota_bookings = chan_df[chan_df['channel'].str.contains('OTA')]['bookings'].sum()
        ota_pct = round(ota_bookings / max(total_bookings, 1) * 100, 1)
        commission_leak = round(chan_df['gross_revenue'].sum() - chan_df['net_revenue'].sum(), 2)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Bookings", total_bookings)
        c2.metric("OTA Share", f"{ota_pct}%",
                  delta_color="inverse" if ota_pct > 50 else "normal")
        c3.metric("Gross Revenue", f"${chan_df['gross_revenue'].sum():,.0f}")
        c4.metric("Commission Leak", f"${commission_leak:,.0f}",
                  delta_color="inverse")

        st.markdown("---")

        col_l, col_r = st.columns(2)

        with col_l:
            fig_chan = px.pie(
                chan_df, values='bookings', names='channel',
                title="Booking Channel Distribution",
                template="plotly_dark",
                hole=0.4,
                color_discrete_sequence=['#4f8ef7', '#ff6b6b', '#ffaa00', '#00cc66', '#7c4dff', '#ff9ff3'],
            )
            fig_chan.update_layout(paper_bgcolor="#0f1117", height=400)
            st.plotly_chart(fig_chan, use_container_width=True)

        with col_r:
            fig_margin = go.Figure()
            fig_margin.add_trace(go.Bar(
                x=chan_df['channel'], y=chan_df['gross_revenue'],
                name='Gross Revenue', marker_color='#4f8ef7',
            ))
            fig_margin.add_trace(go.Bar(
                x=chan_df['channel'], y=chan_df['net_revenue'],
                name='Net Revenue', marker_color='#00cc66',
            ))
            fig_margin.update_layout(
                title="Gross vs Net Revenue by Channel",
                template="plotly_dark",
                paper_bgcolor="#0f1117",
                plot_bgcolor="#1a1d2e",
                height=400,
                barmode='group',
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig_margin, use_container_width=True)

        if ota_pct > 50:
            st.markdown(
                f'<div class="alert-amber">'
                f'⚠️ <strong>OTA Dependency Warning:</strong> {ota_pct}% of bookings '
                f'come from OTAs. Commission cost: ${commission_leak:,.0f}. '
                f'Consider direct booking incentives to improve margins.'
                f'</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════
# PAGE 4 — MEMORY LOG
# ═══════════════════════════════════════════════════════════════
elif page == "🧠 Memory Log":
    st.title("🧠 Agent Memory Log")
    st.caption("Persistent memory across sessions — briefings, anomalies, and conversations")
    st.divider()

    stats = memory.get_stats()

    m1, m2, m3 = st.columns(3)
    m1.metric("Past Briefings", stats['total_briefings'])
    m2.metric("Anomalies Tracked", stats['total_anomalies'])
    m3.metric("Chat Messages", stats['total_chat_messages'])

    st.markdown("---")

    tab_b, tab_a, tab_c = st.tabs(["📋 Past Briefings", "🚨 Anomalies", "💬 Chat History"])

    with tab_b:
        briefings = memory.get_past_briefings(5)
        if briefings:
            for i, b in enumerate(briefings):
                with st.expander(f"Briefing #{i+1}", expanded=(i == 0)):
                    st.markdown(b)
        else:
            st.info("No past briefings stored yet. Generate your first briefing on the Morning Briefing page!")

    with tab_a:
        anomalies = memory.get_recurring_anomalies()
        if anomalies:
            for desc, meta in anomalies:
                severity = meta.get('severity', 'medium')
                alert_class = 'alert-red' if severity == 'high' else 'alert-amber' if severity == 'medium' else 'alert-green'
                st.markdown(
                    f'<div class="{alert_class}">'
                    f'<strong>[{meta.get("type", "unknown")}]</strong> {meta.get("date", "")} — {desc}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No anomalies tracked yet. They will appear after generating briefings.")

    with tab_c:
        chat_history = memory.get_chat_history(20)
        if chat_history:
            for msg in chat_history:
                role = msg['role']
                icon = "👤" if role == "gm" else "🤖"
                st.markdown(f"**{icon} {role.upper()}:** {msg['content'][:500]}")
                st.markdown("---")
        else:
            st.info("No chat history yet. Start a conversation on the Ask the Agent page!")
