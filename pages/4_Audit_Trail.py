"""Audit Trail page — Institutional Research Terminal."""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd

from persistence.audit_log import AuditLogger
from persistence.database import Database
from persistence.thesis_store import ThesisStore
from ui.styles import (
    inject, ACCENT, POSITIVE, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, BG_CARD, BG_PANEL, BORDER,
    FONT_MONO, PLOTLY_LAYOUT,
)
from ui.components import (
    render_kpi_row, alert_card, divider, confidence_bar,
    kpi_card, panel_header, badge, render_hbar,
)
from ui.header import render_header

st.set_page_config(page_title="Audit Trail | IIS", layout="wide")
inject()
render_header()

audit = AuditLogger()
db = Database()

decisions = audit.get_timeline(limit=500)
tool_calls = audit.get_tool_call_history(limit=500)

llm_calls = sum(1 for d in decisions if d.get("action") == "agent_output")
avg_latency = 0.0
if tool_calls:
    latencies = [tc.get("latency_ms", 0) for tc in tool_calls if tc.get("latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

render_kpi_row([
    ("Total Decisions", str(len(decisions)), "", "neutral"),
    ("Tool Calls", str(len(tool_calls)), "MCP", "neutral"),
    ("LLM Invocations", str(llm_calls), "agent runs", "neutral"),
    ("Avg Latency", f"{avg_latency:.0f}ms", "tool calls", "neutral"),
])

divider()

tab_timeline, tab_tools, tab_agents, tab_drift, tab_portfolio, tab_mcp, tab_llm = st.tabs([
    "Timeline", "Tool Calls", "Agent Outputs",
    "Drift History", "Portfolio History",
    "MCP Servers", "LLM Usage Map",
])

# ── Decision Timeline ─────────────────────────────────────────────────
with tab_timeline:
    panel_header("Decision Timeline", "Institutional memory")

    limit = st.slider("Show entries", 10, 200, 50, 10, key="timeline_limit")
    timeline_decisions = decisions[:limit]

    if timeline_decisions:
        action_colors = {
            "trade_approved": POSITIVE, "trade_rejected": DANGER,
            "portfolio_committed": ACCENT, "agent_output": "#a78bfa",
            "policy_change": WARNING, "kill_switch": DANGER,
            "thesis_created": "#38bdf8", "thesis_drift": "#fb923c",
            "constraint_alert": WARNING, "pm_note": TEXT_DIM,
        }

        for d in timeline_decisions:
            ts = d.get("timestamp", "")
            action = d.get("action", "")
            agent_name = d.get("agent_name", "")
            ticker_val = d.get("ticker", "")
            pm_note = d.get("pm_rationale", "")

            color = action_colors.get(action, TEXT_DIM)

            ticker_html = f' \u2014 <strong style="color:{TEXT_PRIMARY};">{ticker_val}</strong>' if ticker_val else ""
            agent_html = f' \u00b7 <span style="color:{TEXT_DIM};">{agent_name}</span>' if agent_name else ""
            pm_html = ""
            if pm_note:
                pm_html = (
                    f'<div style="margin-top:4px;padding:6px 10px;background:{BG_PANEL};'
                    f'border-radius:3px;font-size:0.78rem;color:{TEXT_MUTED};">'
                    f'<strong>PM:</strong> {pm_note}</div>'
                )

            st.markdown(
                f'<div class="t-timeline">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div>'
                f'<span style="font-weight:600;color:{color};font-size:0.85rem;">'
                f'{action.replace("_", " ").title()}</span>'
                f'{ticker_html}{agent_html}'
                f'</div>'
                f'<div style="color:{TEXT_DIM};font-size:0.72rem;font-family:{FONT_MONO};">{ts}</div>'
                f'</div>'
                f'{pm_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Details", expanded=False):
                details = d.get("details_json", "{}")
                try:
                    st.json(json.loads(details) if isinstance(details, str) else details)
                except Exception:
                    st.text(str(details)[:1000])
    else:
        st.markdown(
            alert_card("info", "No Decisions Yet",
                       "Start using the app \u2014 actions will appear here.",
                       "Builds institutional decision memory"),
            unsafe_allow_html=True,
        )

# ── Tool Call Log ─────────────────────────────────────────────────────
with tab_tools:
    panel_header("Tool Call Log", "MCP compliance")

    if tool_calls:
        servers: dict[str, int] = {}
        successes = 0
        for tc in tool_calls:
            srv = tc.get("server_name", "unknown")
            servers[srv] = servers.get(srv, 0) + 1
            if tc.get("success"):
                successes += 1

        success_rate = (successes / len(tool_calls) * 100) if tool_calls else 0

        render_kpi_row([
            ("Total Calls", str(len(tool_calls)), "", "neutral"),
            ("Unique Servers", str(len(servers)), "", "neutral"),
            ("Success Rate", f"{success_rate:.0f}%", "",
             "pos" if success_rate > 95 else "neg" if success_rate < 80 else "neutral"),
            ("Cached", str(sum(1 for tc in tool_calls if tc.get("cached"))), "", "neutral"),
        ])

        if servers:
            render_hbar(
                list(servers.keys()),
                list(servers.values()),
                title="Calls by MCP Server",
                height=200,
                color_by_sign=False,
            )

        divider()

        latency_data = [tc.get("latency_ms", 0) for tc in tool_calls if tc.get("latency_ms")]
        if latency_data:
            import plotly.express as px
            fig = px.histogram(
                x=latency_data, nbins=30,
                labels={"x": "Latency (ms)", "y": "Count"},
                title="Tool Call Latency Distribution",
            )
            fig.update_layout(
                height=220,
                **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis", "margin")},
                margin=dict(t=36, b=30, l=40, r=20),
            )
            fig.update_traces(marker_color=ACCENT)
            st.plotly_chart(fig, use_container_width=True)

        divider()

        df = pd.DataFrame(tool_calls)
        display_cols = [c for c in [
            "timestamp", "server_name", "tool_name", "latency_ms", "success", "cached",
        ] if c in df.columns]
        st.dataframe(df[display_cols] if display_cols else df,
                     use_container_width=True, hide_index=True, height=360)

        selected_idx = st.number_input("View details for row #", 0, len(tool_calls) - 1, 0)
        if selected_idx < len(tool_calls):
            st.json(tool_calls[selected_idx])
    else:
        st.markdown(
            alert_card("info", "No Tool Calls",
                       "Run any agent or data fetch to see calls logged here.", ""),
            unsafe_allow_html=True,
        )

# ── Agent Outputs ─────────────────────────────────────────────────────
with tab_agents:
    panel_header("Agent Outputs")

    agent_outputs = [d for d in decisions if d.get("action") == "agent_output"]

    if agent_outputs:
        by_agent: dict[str, list] = {}
        for d in agent_outputs:
            ag = d.get("agent_name", "unknown")
            by_agent.setdefault(ag, []).append(d)

        for agent_name, outputs in by_agent.items():
            st.markdown(
                f'<span style="font-weight:600;color:{ACCENT};font-size:0.85rem;">{agent_name}</span> '
                f'{badge(str(len(outputs)), "neutral")}',
                unsafe_allow_html=True,
            )
            for d in outputs[:10]:
                ts = d.get("timestamp", "")
                ticker_val = d.get("ticker", "")
                label = f"{ts}" + (f" \u2014 {ticker_val}" if ticker_val else "")
                with st.expander(label):
                    details = d.get("details_json", "{}")
                    try:
                        st.json(json.loads(details) if isinstance(details, str) else details)
                    except Exception:
                        st.text(str(details)[:2000])
    else:
        st.markdown(
            alert_card("info", "No Agent Outputs",
                       "Run agents from Equity Research or Portfolio Manager.", ""),
            unsafe_allow_html=True,
        )

# ── Thesis Drift History ─────────────────────────────────────────────
with tab_drift:
    panel_header("Thesis Drift Alerts History")

    store = ThesisStore()
    all_theses = store.get_all(limit=20)

    if all_theses:
        thesis_options = {f"{t.ticker} \u2014 {t.thesis_id[:8]}": t.thesis_id for t in all_theses}
        selected = st.selectbox("Select thesis", list(thesis_options.keys()))
        thesis_id = thesis_options.get(selected, "")

        if thesis_id:
            drift_history = store.get_drift_history(thesis_id=thesis_id)
            if drift_history:
                status_counts = {"no_change": 0, "weakened": 0, "invalidated": 0, "strengthened": 0}
                for dc in drift_history:
                    s = dc.get("status", "no_change")
                    status_counts[s] = status_counts.get(s, 0) + 1

                render_kpi_row([
                    ("No Change", str(status_counts["no_change"]), "", "neutral"),
                    ("Strengthened", str(status_counts["strengthened"]), "", "pos"),
                    ("Weakened", str(status_counts["weakened"]), "", "neg"),
                    ("Invalidated", str(status_counts["invalidated"]), "", "neg"),
                ])

                divider()

                for dc in drift_history:
                    status = dc.get("status", "no_change")
                    sev = {"no_change": "info", "weakened": "warning",
                           "invalidated": "critical", "strengthened": "success"}.get(status, "info")
                    st.markdown(
                        alert_card(sev,
                                   f"{status.replace('_', ' ').title()} \u2014 {dc.get('claim_id', '')}",
                                   dc.get("evidence", "No evidence recorded"),
                                   f"Checked: {dc.get('timestamp', '')}"),
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No drift checks recorded.")
    else:
        st.markdown(
            alert_card("info", "No Theses Saved",
                       "Generate a thesis from Equity Research first.", ""),
            unsafe_allow_html=True,
        )

# ── Portfolio History ─────────────────────────────────────────────────
with tab_portfolio:
    panel_header("Portfolio Version History")

    history = db.get_portfolio_history(limit=50)
    if history:
        for h in history:
            ver = h.get("version", "?")
            ts = h.get("timestamp", "")
            notes = h.get("notes", "")
            positions = h.get("positions", [])

            with st.expander(f"v{ver} \u2014 {ts} ({len(positions)} positions)"):
                if notes:
                    st.markdown(
                        f'<div style="padding:6px 10px;background:{BG_PANEL};'
                        f'border-radius:3px;font-size:0.8rem;color:{TEXT_MUTED};margin-bottom:6px;">'
                        f'<strong>Notes:</strong> {notes}</div>',
                        unsafe_allow_html=True,
                    )
                if positions:
                    st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True)
    else:
        st.markdown(
            alert_card("info", "No History",
                       "Save a portfolio to start building history.", ""),
            unsafe_allow_html=True,
        )

# ── MCP Servers ──────────────────────────────────────────────────────
with tab_mcp:
    panel_header("MCP Server Registry", "FastMCP SDK")

    from mcp_servers.client import MCPClient, SERVER_REGISTRY

    transport = st.radio(
        "Transport mode",
        ["direct (in-process)", "stdio (subprocess JSON-RPC)"],
        horizontal=True,
    )
    mode = "direct" if transport.startswith("direct") else "stdio"

    render_kpi_row([
        ("Servers", str(len(SERVER_REGISTRY)), "", "neutral"),
        ("Transport", mode.upper(), "", "pos" if mode == "stdio" else "neutral"),
        ("Protocol", "JSON-RPC 2.0", "", "neutral"),
        ("SDK", "mcp v1.26", "", "neutral"),
    ])
    divider()

    if st.button("Discover all tools", type="primary", key="mcp_discover"):
        mcp_client = MCPClient(mode=mode, log_calls=False)
        total_tools = 0
        for sname, sinfo in SERVER_REGISTRY.items():
            with st.expander(f"{sname} \u2014 `{sinfo['script']}`", expanded=True):
                try:
                    tools = mcp_client.list_tools(sname)
                    total_tools += len(tools)
                    for t in tools:
                        st.markdown(
                            f'<div style="padding:4px 8px;margin:3px 0;background:rgba(91,155,213,0.06);'
                            f'border-left:2px solid {ACCENT};border-radius:3px;">'
                            f'<code style="font-weight:600;color:{TEXT_PRIMARY};">{t["name"]}</code> '
                            f'<span style="color:{TEXT_DIM};font-size:0.78rem;">'
                            f'\u2014 {t["description"][:80]}</span></div>',
                            unsafe_allow_html=True,
                        )
                        if t.get("schema"):
                            with st.popover("Schema"):
                                st.json(t["schema"])
                except Exception as exc:
                    st.error(f"Failed: {exc}")

        st.success(f"Discovered {total_tools} tools across {len(SERVER_REGISTRY)} servers ({mode})")

    with st.expander("MCP Architecture"):
        st.code("""
Streamlit UI
    |
Wrapper Classes (AlphaVantageMCP, FredMCP, ...)
    |
MCPClient (mode: direct or stdio)
    | (direct)               | (stdio)
Import server module    Spawn subprocess
Call @mcp.tool()        JSON-RPC 2.0 over stdin/stdout
    |                        |
FastMCP Server (tool definitions, validation, schemas)
    |
External APIs (Alpha Vantage, FRED, SEC, GDELT, FMP)
""", language="text")

# ── LLM Usage Map ────────────────────────────────────────────────────
with tab_llm:
    panel_header("LLM Usage Map", "Transparency")

    llm_agents = [
        ("Market Narrative", "Regime assessment from macro, news, market data"),
        ("Equity Analyst", "Bull/bear thesis with catalysts, risks, valuation signal"),
        ("Transcript Analyst", "Earnings call intelligence extraction"),
        ("News Sentiment", "Per-article sentiment scoring and categorization"),
        ("Risk Analytics", "Quantitative risk interpretation in context"),
        ("Asset Manager", "Portfolio weight change proposals"),
        ("Decision Synthesizer", "Final committee decision note and vote"),
        ("Drift Detector", "Thesis claim validity re-evaluation"),
        ("Scenario Generator", "Custom stress scenarios from current context"),
    ]

    hardcoded_modules = [
        ("Portfolio Metrics", "Vol, VaR, Sharpe, drawdown \u2014 pure math"),
        ("Factor Model", "Fama-French OLS regression \u2014 deterministic"),
        ("Constraints Engine", "Position/sector limits \u2014 governance rules"),
        ("Autopilot Validator", "AUTO/REVIEW classification \u2014 compliance boundary"),
        ("Stress Test Library", "6 fixed factor-shock scenarios \u2014 reproducibility"),
    ]

    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:600;color:{TEXT_PRIMARY};margin-bottom:8px;">'
        f'LLM-Powered {badge(str(len(llm_agents)), "paper")}</div>',
        unsafe_allow_html=True,
    )
    for name, desc in llm_agents:
        st.markdown(
            f'<div style="padding:4px 0;border-bottom:1px solid {BORDER};">'
            f'<span style="font-weight:500;color:{TEXT_PRIMARY};font-size:0.82rem;">{name}</span> '
            f'<span style="color:{TEXT_DIM};font-size:0.75rem;">\u2014 {desc}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    divider()

    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:600;color:{TEXT_PRIMARY};margin-bottom:8px;">'
        f'Deterministic {badge(str(len(hardcoded_modules)), "neutral")}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Deliberately NOT LLM-powered \u2014 governance and math must be exact")
    for name, desc in hardcoded_modules:
        st.markdown(
            f'<div style="padding:4px 0;border-bottom:1px solid {BORDER};">'
            f'<span style="font-weight:500;color:{TEXT_PRIMARY};font-size:0.82rem;">{name}</span> '
            f'<span style="color:{TEXT_DIM};font-size:0.75rem;">\u2014 {desc}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
