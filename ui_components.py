"""Reusable UI components with psychology-backed design patterns.

Principles applied:
- Loss Aversion (Kahneman): frame risk in terms of what you could lose
- Zeigarnik Effect: incomplete indicators pull users back
- Peak-End Rule: make decision moments memorable
- Variable Reward (Hook Model): fresh data and insights each visit
- Endowment Effect: users value what they build (portfolio, theses)
- Cognitive Fluency: consistent visual patterns reduce friction
- Authority/Trust: institutional-grade typography and layout
- Color Psychology: trust (blue), urgency (amber/red), success (green)
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from typing import Any

# ── Global Theme ──────────────────────────────────────────────────────

THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Base typography — Inter is the most trusted UI typeface in finance */
    .stApp, .stMarkdown, .stText {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Reduce visual noise — calmer backgrounds for sustained focus */
    .stApp > header { background: transparent; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1419 0%, #1a2332 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* KPI card styling — Gestalt proximity groups related metrics */
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 4px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .kpi-delta-pos { color: #16a34a; font-size: 0.85rem; font-weight: 500; }
    .kpi-delta-neg { color: #dc2626; font-size: 0.85rem; font-weight: 500; }
    .kpi-delta-neutral { color: #64748b; font-size: 0.85rem; font-weight: 500; }

    /* Health score ring — creates immediate visual anchor */
    .health-ring {
        text-align: center;
        padding: 12px;
    }

    /* Alert cards — loss aversion framing makes risks tangible */
    .alert-critical {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border-left: 4px solid #dc2626;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .alert-warning {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .alert-info {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }
    .alert-success {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 4px solid #16a34a;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
    }

    /* Thesis cards — endowment effect: own your analysis */
    .thesis-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px;
        margin: 12px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .thesis-bull { border-top: 3px solid #16a34a; }
    .thesis-bear { border-top: 3px solid #dc2626; }
    .thesis-neutral { border-top: 3px solid #64748b; }

    /* Confidence badge — authority signaling */
    .confidence-high {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .confidence-mid {
        display: inline-block;
        background: #fef3c7;
        color: #92400e;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .confidence-low {
        display: inline-block;
        background: #fee2e2;
        color: #991b1b;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Vote badges for IC mode — social proof anchoring */
    .vote-buy {
        display: inline-block;
        background: linear-gradient(135deg, #16a34a, #15803d);
        color: white;
        padding: 8px 24px;
        border-radius: 24px;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .vote-hold {
        display: inline-block;
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 8px 24px;
        border-radius: 24px;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .vote-sell {
        display: inline-block;
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        color: white;
        padding: 8px 24px;
        border-radius: 24px;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    /* Timeline styling — narrative arc for audit trail */
    .timeline-entry {
        border-left: 2px solid #e2e8f0;
        padding: 12px 0 12px 24px;
        margin-left: 12px;
        position: relative;
    }
    .timeline-entry::before {
        content: '';
        width: 12px;
        height: 12px;
        background: #3b82f6;
        border-radius: 50%;
        position: absolute;
        left: -7px;
        top: 16px;
    }

    /* Pulse animation for live indicators — variable reward anticipation */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #16a34a;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }

    /* Smooth section dividers */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
        margin: 24px 0;
    }

    /* Action buttons — commitment and consistency principle */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }

    /* Hide default Streamlit footer for cleaner institutional look */
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
</style>
"""


def inject_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


# ── KPI Card ──────────────────────────────────────────────────────────

def kpi_card(label: str, value: str, delta: str = "", delta_type: str = "neutral") -> str:
    delta_class = f"kpi-delta-{delta_type}"
    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def render_kpi_row(kpis: list[tuple[str, str, str, str]]) -> None:
    """Render a row of KPI cards. Each tuple: (label, value, delta, delta_type)."""
    cols = st.columns(len(kpis))
    for col, (label, value, delta, dtype) in zip(cols, kpis):
        with col:
            st.markdown(kpi_card(label, value, delta, dtype), unsafe_allow_html=True)


# ── Health Score Gauge ────────────────────────────────────────────────

def portfolio_health_score(
    n_positions: int,
    cash_weight: float,
    top5_conc: float,
    constraint_violations: int,
    has_thesis: bool = False,
) -> tuple[int, str]:
    """Compute a 0-100 health score with interpretation.

    Gamification: a single number that creates ownership and
    motivates improvement (Zeigarnik effect for incomplete scores).
    """
    score = 100

    if n_positions < 5:
        score -= 20
    elif n_positions < 10:
        score -= 5

    if cash_weight < 0.02:
        score -= 15
    elif cash_weight > 0.30:
        score -= 10

    if top5_conc > 0.60:
        score -= 20
    elif top5_conc > 0.45:
        score -= 10

    score -= constraint_violations * 10

    if not has_thesis:
        score -= 10

    score = max(0, min(100, score))

    if score >= 80:
        label = "Excellent"
    elif score >= 60:
        label = "Good"
    elif score >= 40:
        label = "Needs Attention"
    else:
        label = "At Risk"

    return score, label


def render_health_gauge(score: int, label: str) -> None:
    """Render a radial gauge for portfolio health — immediate visual anchor."""
    if score >= 80:
        color = "#16a34a"
    elif score >= 60:
        color = "#f59e0b"
    elif score >= 40:
        color = "#f97316"
    else:
        color = "#dc2626"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "", "font": {"size": 48, "family": "Inter", "color": "#0f172a"}},
        title={"text": f"Portfolio Health — {label}",
               "font": {"size": 14, "family": "Inter", "color": "#64748b"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "white",
                     "dtick": 25, "tickfont": {"size": 10, "color": "#94a3b8"}},
            "bar": {"color": color, "thickness": 0.7},
            "bgcolor": "#f1f5f9",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "#fef2f2"},
                {"range": [40, 60], "color": "#fffbeb"},
                {"range": [60, 80], "color": "#f0fdf4"},
                {"range": [80, 100], "color": "#dcfce7"},
            ],
            "threshold": {
                "line": {"color": "#0f172a", "width": 2},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=30, r=30, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter"},
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Confidence Meter ──────────────────────────────────────────────────

def confidence_badge(confidence: float) -> str:
    """Visual confidence indicator — authority signaling."""
    pct = f"{confidence:.0%}"
    if confidence >= 0.75:
        return f'<span class="confidence-high">{pct} confidence</span>'
    elif confidence >= 0.50:
        return f'<span class="confidence-mid">{pct} confidence</span>'
    else:
        return f'<span class="confidence-low">{pct} confidence</span>'


def render_confidence_bar(confidence: float, label: str = "") -> None:
    """Horizontal confidence bar with color gradient."""
    if confidence >= 0.75:
        color = "#16a34a"
    elif confidence >= 0.50:
        color = "#f59e0b"
    else:
        color = "#dc2626"

    pct = int(confidence * 100)
    html = f"""
    <div style="margin: 8px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">{label}</span>
            <span style="font-size: 0.8rem; color: {color}; font-weight: 700;">{pct}%</span>
        </div>
        <div style="background: #f1f5f9; border-radius: 6px; height: 8px; overflow: hidden;">
            <div style="background: {color}; height: 100%; width: {pct}%; border-radius: 6px;
                        transition: width 0.6s ease;"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ── Alert Cards (Loss Aversion framing) ──────────────────────────────

def alert_card(severity: str, title: str, message: str, action_hint: str = "") -> str:
    css_class = {
        "critical": "alert-critical",
        "warning": "alert-warning",
        "info": "alert-info",
        "success": "alert-success",
    }.get(severity, "alert-info")
    icon = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅",
    }.get(severity, "ℹ️")
    action_html = f'<div style="margin-top:8px;font-size:0.8rem;color:#64748b;font-style:italic;">{action_hint}</div>' if action_hint else ""
    return f"""
    <div class="{css_class}">
        <div style="font-weight:600;margin-bottom:4px;">{icon} {title}</div>
        <div style="font-size:0.9rem;color:#374151;">{message}</div>
        {action_html}
    </div>
    """


# ── Vote Badge ────────────────────────────────────────────────────────

def vote_badge(vote: str) -> str:
    v = vote.lower().strip()
    css = {"buy": "vote-buy", "hold": "vote-hold", "sell": "vote-sell"}.get(v, "vote-hold")
    return f'<span class="{css}">{vote.upper()}</span>'


# ── Section Divider ───────────────────────────────────────────────────

def divider() -> None:
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ── Live Indicator ────────────────────────────────────────────────────

def live_indicator(text: str = "Live") -> str:
    return f'<span><span class="live-dot"></span>{text}</span>'


# ── Donut Chart (for sector/weight breakdown) ─────────────────────────

def render_donut(labels: list[str], values: list[float], title: str = "",
                 height: int = 300) -> None:
    colors = [
        "#3b82f6", "#16a34a", "#f59e0b", "#ef4444", "#8b5cf6",
        "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
        "#14b8a6", "#e11d48",
    ]
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors[:len(labels)],
                    line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11, family="Inter"),
        hoverinfo="label+value+percent",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Inter", color="#374151")),
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font={"family": "Inter"},
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Horizontal Bar Chart (for factor betas, stress impacts) ──────────

def render_hbar(labels: list[str], values: list[float], title: str = "",
                height: int = 250, color_by_sign: bool = True) -> None:
    colors = [("#16a34a" if v >= 0 else "#dc2626") for v in values] if color_by_sign else ["#3b82f6"] * len(values)
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"{v:+.2f}" for v in values],
        textposition="outside",
        textfont=dict(size=11, family="Inter"),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Inter", color="#374151")),
        height=height,
        margin=dict(l=10, r=60, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=True,
                   zerolinecolor="#94a3b8", zerolinewidth=1),
        yaxis=dict(automargin=True),
        font={"family": "Inter"},
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Progress Steps (Zeigarnik effect — incomplete tasks draw return) ──

def render_workflow_steps(steps: list[tuple[str, str]], current: int = 0) -> None:
    """Show workflow progress. Each step: (name, status: done|active|pending)."""
    cols = st.columns(len(steps))
    for i, (col, (name, status)) in enumerate(zip(cols, steps)):
        with col:
            if status == "done":
                icon = "✅"
                color = "#16a34a"
            elif status == "active":
                icon = "🔄"
                color = "#3b82f6"
            else:
                icon = "⬜"
                color = "#94a3b8"
            st.markdown(
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.5rem;">{icon}</div>'
                f'<div style="font-size:0.75rem;color:{color};font-weight:600;">{name}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Streak Counter (Variable reward — gamification) ───────────────────

def render_streak(count: int, label: str = "decisions this session") -> None:
    if count == 0:
        return
    st.markdown(
        f'<div style="text-align:center;padding:8px;background:linear-gradient(135deg,#eff6ff,#dbeafe);'
        f'border-radius:12px;margin:8px 0;">'
        f'<span style="font-size:1.5rem;">🔥</span> '
        f'<span style="font-size:1.1rem;font-weight:700;color:#1e40af;">{count}</span> '
        f'<span style="font-size:0.85rem;color:#3b82f6;">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
