"""Investment Intelligence Studio — Home Dashboard."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime

from config import settings, DB_PATH
from persistence.database import Database
from persistence.audit_log import AuditLogger
from schemas.policy import Policy
from schemas.portfolio import PortfolioState, Position
from ui.styles import inject, ACCENT, POSITIVE, DANGER, WARNING, TEXT_DIM, TEXT_MUTED, TEXT_PRIMARY, BG_CARD, BORDER, FONT_MONO
from ui.components import (
    render_kpi_row, portfolio_health_score, render_health_gauge,
    alert_card, divider, live_dot, render_donut, panel_header, badge,
)
from ui.header import render_header

st.set_page_config(
    page_title="Investment Intelligence Studio",
    page_icon="IIS",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject()

# ── Session state init ────────────────────────────────────────────────

if "portfolio" not in st.session_state:
    db = Database()
    saved = db.get_latest_portfolio()
    if saved:
        try:
            st.session_state.portfolio = PortfolioState.model_validate(saved)
        except Exception:
            st.session_state.portfolio = PortfolioState()
    else:
        st.session_state.portfolio = PortfolioState()

if "policy" not in st.session_state:
    db = Database()
    saved_policy = db.get_policy("default")
    if saved_policy:
        try:
            st.session_state.policy = Policy.model_validate(saved_policy)
        except Exception:
            st.session_state.policy = Policy()
    else:
        st.session_state.policy = Policy()

if "autopilot_mode" not in st.session_state:
    st.session_state.autopilot_mode = "hybrid"
if "kill_switch" not in st.session_state:
    st.session_state.kill_switch = False
if "committee_results" not in st.session_state:
    st.session_state.committee_results = None
if "session_decisions" not in st.session_state:
    st.session_state.session_decisions = 0

portfolio: PortfolioState = st.session_state.portfolio

# ── Sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<div style="padding:8px 0 16px;">'
        f'<div style="font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY};letter-spacing:-0.02em;">IIS</div>'
        f'<div style="font-size:0.7rem;color:{TEXT_DIM};margin-top:2px;">Investment Intelligence Studio</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:4px;padding:12px;margin:4px 0;">'
        f'<div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;color:{TEXT_DIM};">Portfolio</div>'
        f'<div style="font-size:1.3rem;font-weight:700;color:{TEXT_PRIMARY};font-family:{FONT_MONO};">v{portfolio.version}</div>'
        f'<div style="font-size:0.75rem;color:{TEXT_MUTED};">'
        f'{len(portfolio.positions)} positions &middot; {portfolio.cash_weight:.1%} cash</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f'<div style="height:12px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:{TEXT_DIM};margin-bottom:4px;">Governance</div>',
        unsafe_allow_html=True,
    )

    kill = st.toggle("Kill Switch", value=st.session_state.kill_switch)
    st.session_state.kill_switch = kill
    if kill:
        st.markdown(
            f'<div style="background:rgba(248,113,113,0.1);color:{DANGER};'
            f'padding:6px 10px;border-radius:3px;font-size:0.75rem;font-weight:600;'
            f'border:1px solid rgba(248,113,113,0.3);">'
            f'KILL SWITCH ACTIVE</div>',
            unsafe_allow_html=True,
        )

    mode = st.radio(
        "Autopilot Mode",
        options=["full_manual", "hybrid", "full_auto"],
        index=1,
        format_func=lambda x: {"full_manual": "Manual", "hybrid": "Hybrid", "full_auto": "Auto"}[x],
    )
    st.session_state.autopilot_mode = mode

    st.markdown(f'<div style="height:12px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:{TEXT_DIM};margin-bottom:4px;">Data Sources</div>',
        unsafe_allow_html=True,
    )
    api_checks = {
        "Market Data (yfinance)": True,
        "News (yfinance)": True,
        "Earnings (yfinance)": True,
        "FRED Macro": bool(settings.FRED_API_KEY),
        "SEC EDGAR": True,
        "Azure OpenAI": settings.use_azure,
    }
    for name, ok in api_checks.items():
        dot = POSITIVE if ok else DANGER
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
            f'<div style="width:5px;height:5px;background:{dot};border-radius:50%;"></div>'
            f'<span style="font-size:0.75rem;color:{TEXT_MUTED};">{name}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Header ────────────────────────────────────────────────────────────

render_header()

# ── KPI Row ───────────────────────────────────────────────────────────

weights = [p.weight for p in portfolio.positions]
sorted_w = sorted(weights, reverse=True) if weights else [0]
top5 = sum(sorted_w[:5])

from quant.constraints import ConstraintsEngine
engine = ConstraintsEngine(st.session_state.policy)
alerts = engine.check_portfolio(portfolio)
n_violations = len(alerts)

from persistence.thesis_store import ThesisStore
store = ThesisStore()
has_theses = len(store.get_all(limit=1)) > 0

total_weight = sum(p.weight for p in portfolio.positions) + portfolio.cash_weight

render_kpi_row([
    ("Positions", str(len(portfolio.positions)), "", "neutral"),
    ("Cash", f"{portfolio.cash_weight:.1%}", "", "neutral"),
    ("Allocation", f"{total_weight:.1%}",
     "Fully allocated" if abs(total_weight - 1.0) < 0.01 else f"{(1-total_weight):.1%} gap",
     "pos" if abs(total_weight - 1.0) < 0.01 else "neg"),
    ("Violations", str(n_violations),
     "Clear" if n_violations == 0 else f"{n_violations} alerts",
     "pos" if n_violations == 0 else "neg"),
])

divider()

# ── Three-column layout: health | positions | alerts ──────────────────

col_health, col_positions, col_alerts = st.columns([1, 2, 1.5])

with col_health:
    score, label = portfolio_health_score(
        len(portfolio.positions), portfolio.cash_weight, top5, n_violations, has_theses
    )
    render_health_gauge(score, label)

with col_positions:
    panel_header("Holdings", f"{len(portfolio.positions)} positions")
    if portfolio.positions:
        df = pd.DataFrame([
            {"Ticker": p.ticker, "Wt%": f"{p.weight:.1%}", "Sector": p.sector or "\u2014"}
            for p in portfolio.positions
        ])
        st.dataframe(df, use_container_width=True, hide_index=True,
                      height=min(len(df) * 38 + 38, 280))
    else:
        st.markdown(
            alert_card("info", "Empty Portfolio",
                       "Navigate to Portfolio Manager to add positions.",
                       "Start with 5\u201310 diversified names for reliable analytics."),
            unsafe_allow_html=True,
        )

with col_alerts:
    panel_header("Constraint Monitor", live_dot("Live"))
    if alerts:
        for a in alerts[:5]:
            sev = a.rule.severity.value
            hint = {
                "critical": "Immediate action required",
                "warning": "Review at next rebalance",
                "info": "For reference",
            }.get(sev, "")
            st.markdown(alert_card(sev, a.rule.name, a.message, hint), unsafe_allow_html=True)
    else:
        st.markdown(
            alert_card("success", "All Clear", "Portfolio within all policy limits.", ""),
            unsafe_allow_html=True,
        )

# ── Allocation breakdown ─────────────────────────────────────────────

if portfolio.positions:
    divider()
    col_donut, col_nav = st.columns([1, 1])
    with col_donut:
        sector_weights: dict[str, float] = {}
        for pos in portfolio.positions:
            s = pos.sector or "Other"
            sector_weights[s] = sector_weights.get(s, 0.0) + pos.weight
        if portfolio.cash_weight > 0:
            sector_weights["Cash"] = portfolio.cash_weight
        render_donut(
            list(sector_weights.keys()),
            [round(v * 100, 2) for v in sector_weights.values()],
            title="Allocation Breakdown",
        )
    with col_nav:
        panel_header("Quick Navigation")
        pages = [
            ("Equity Research", "Single-stock deep dives, thesis generation, AI transcript analysis"),
            ("Portfolio Manager", "Construction, risk dashboard, rebalancing, factor exposures"),
            ("Market & News", "Macro regime detection, news flow, catalyst calendar"),
            ("Audit Trail", "Decision timeline, tool calls, thesis drift, MCP health"),
        ]
        for name, desc in pages:
            st.markdown(
                f'<div style="padding:6px 0;border-bottom:1px solid {BORDER};">'
                f'<div style="font-size:0.85rem;font-weight:600;color:{TEXT_PRIMARY};">{name}</div>'
                f'<div style="font-size:0.72rem;color:{TEXT_DIM};">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Footer ────────────────────────────────────────────────────────────

divider()
st.markdown(
    f'<div style="text-align:center;color:{TEXT_DIM};font-size:0.68rem;padding:8px 0;font-family:{FONT_MONO};">'
    f'GOVERNANCE: Agents produce analysis only. Portfolio writes require validated commit functions. '
    f'No agent can directly modify holdings.</div>',
    unsafe_allow_html=True,
)
