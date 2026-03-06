"""Portfolio Manager page — Institutional Research Terminal."""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from schemas.portfolio import PortfolioState, Position, TradePlan, TradeAction, ActionType
from schemas.policy import Policy
from persistence.database import Database
from persistence.audit_log import AuditLogger
from schemas.audit import AuditAction
from quant.constraints import ConstraintsEngine
from quant.stress_testing import StressTestEngine, SCENARIO_LIBRARY
from governance.autopilot import AutopilotValidator, AutopilotMode
from ui.styles import (
    inject, ACCENT, POSITIVE, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, BG_CARD, BG_PANEL, BORDER,
    FONT_MONO, PLOTLY_LAYOUT,
)
from ui.components import (
    render_kpi_row, render_donut, render_hbar, alert_card, divider,
    confidence_bar, confidence_badge_html, vote_badge, render_workflow_steps,
    kpi_card, panel_header, badge,
)
from ui.header import render_header

st.set_page_config(page_title="Portfolio Manager | IIS", layout="wide")
inject()
render_header()

def _load_portfolio_from_db() -> PortfolioState:
    """Try to load the most recent saved portfolio from SQLite."""
    try:
        db = Database()
        latest = db.get_latest_portfolio()
        if latest:
            return PortfolioState.model_validate(latest)
    except Exception:
        pass
    return PortfolioState()


if "portfolio" not in st.session_state:
    st.session_state.portfolio = _load_portfolio_from_db()
if "policy" not in st.session_state:
    st.session_state.policy = Policy()

portfolio: PortfolioState = st.session_state.portfolio
policy: Policy = st.session_state.policy

tab_build, tab_risk, tab_factors, tab_rebalance, tab_stress, tab_committee = st.tabs([
    "Builder", "Risk Dashboard", "Factor Exposures",
    "Rebalance", "Stress Testing", "Investment Committee",
])

# ── Portfolio Builder ─────────────────────────────────────────────────
SECTOR_OPTIONS = [
    "Technology", "Healthcare", "Financials", "Energy",
    "Consumer Discretionary", "Consumer Staples", "Industrials",
    "Materials", "Utilities", "Real Estate", "Communication Services", "Other",
]

with tab_build:
    panel_header("Portfolio Builder", f"{len(portfolio.positions)} positions \u00b7 {portfolio.cash_weight:.1%} cash")

    # ── Load saved portfolio ──
    with st.expander("Load a saved portfolio", expanded=not bool(portfolio.positions)):
        db_inst = Database()
        history = db_inst.get_portfolio_history(limit=10)
        if history:
            options = {}
            for h in history:
                ver = h.get("version", "?")
                ts = h.get("timestamp", "")[:16]
                notes = h.get("notes", "")[:40]
                n_pos = len(h.get("positions", []))
                label = f"v{ver}  |  {ts}  |  {n_pos} positions"
                if notes:
                    label += f"  |  {notes}"
                options[label] = h

            selected_label = st.selectbox(
                "Saved portfolios", list(options.keys()), key="load_port_sel",
            )

            col_load, col_clear = st.columns(2)
            with col_load:
                if st.button("Load Selected", key="load_saved_port", type="primary"):
                    chosen = options[selected_label]
                    try:
                        loaded = PortfolioState.model_validate(chosen)
                        st.session_state.portfolio = loaded
                        st.session_state["_rebalance_msg"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not load: {e}")
            with col_clear:
                if st.button("Start Fresh", key="clear_port"):
                    st.session_state.portfolio = PortfolioState()
                    st.rerun()
        else:
            st.info("No saved portfolios yet. Add positions below and they will be saved automatically.")

    divider()

    # Quick-add row (no form barrier)
    col_t, col_w, col_s, col_btn = st.columns([1.5, 1, 1.5, 0.8])
    with col_t:
        new_ticker = st.text_input("Ticker", max_chars=10, key="add_ticker",
                                   label_visibility="collapsed",
                                   placeholder="Ticker (e.g. AAPL)").upper().strip()
    with col_w:
        new_weight = st.number_input("Wt%", 0.0, 100.0, 5.0, 0.5, key="add_wt",
                                     label_visibility="collapsed") / 100
    with col_s:
        new_sector = st.selectbox("Sector", SECTOR_OPTIONS, key="add_sector",
                                  label_visibility="collapsed")
    with col_btn:
        add_clicked = st.button("Add", type="primary", key="add_pos_btn",
                                use_container_width=True)

    if add_clicked and new_ticker:
        existing = {p.ticker: p for p in portfolio.positions}
        if new_ticker in existing:
            existing[new_ticker].weight = new_weight
            existing[new_ticker].sector = new_sector
        else:
            existing[new_ticker] = Position(
                ticker=new_ticker, weight=new_weight, sector=new_sector
            )
        portfolio.positions = list(existing.values())
        portfolio.cash_weight = max(0, 1.0 - sum(p.weight for p in portfolio.positions))
        st.session_state.portfolio = portfolio
        Database().save_portfolio(portfolio.model_dump_json(), notes="Position added/updated")
        st.rerun()

    divider()

    if portfolio.positions:
        col_table, col_chart = st.columns([3, 2])

        with col_table:
            for pos in sorted(portfolio.positions, key=lambda x: -x.weight):
                c_tick, c_wt, c_sec, c_rm = st.columns([1.2, 1, 1.5, 0.6])
                with c_tick:
                    st.markdown(
                        f'<div style="font-family:{FONT_MONO};font-weight:600;'
                        f'color:{TEXT_PRIMARY};padding-top:6px;">{pos.ticker}</div>',
                        unsafe_allow_html=True,
                    )
                with c_wt:
                    st.markdown(
                        f'<div style="font-family:{FONT_MONO};color:{ACCENT};'
                        f'padding-top:6px;">{pos.weight:.1%}</div>',
                        unsafe_allow_html=True,
                    )
                with c_sec:
                    st.markdown(
                        f'<div style="font-size:0.78rem;color:{TEXT_DIM};'
                        f'padding-top:8px;">{pos.sector or "\u2014"}</div>',
                        unsafe_allow_html=True,
                    )
                with c_rm:
                    if st.button("x", key=f"rm_{pos.ticker}", help=f"Remove {pos.ticker}"):
                        portfolio.positions = [p for p in portfolio.positions if p.ticker != pos.ticker]
                        portfolio.cash_weight = max(0, 1.0 - sum(p.weight for p in portfolio.positions))
                        st.session_state.portfolio = portfolio
                        Database().save_portfolio(portfolio.model_dump_json(), notes=f"Removed {pos.ticker}")
                        st.rerun()

        with col_chart:
            render_kpi_row([
                ("Positions", str(len(portfolio.positions)), "", "neutral"),
                ("Cash", f"{portfolio.cash_weight:.1%}", "", "neutral"),
                ("Invested", f"{(1-portfolio.cash_weight):.1%}", "", "neutral"),
            ])

            render_donut(
                [p.ticker for p in portfolio.positions] + (["Cash"] if portfolio.cash_weight > 0 else []),
                [round(p.weight * 100, 2) for p in portfolio.positions] + (
                    [round(portfolio.cash_weight * 100, 2)] if portfolio.cash_weight > 0 else []),
                title="Position Weights",
                height=260,
            )
    else:
        st.markdown(
            alert_card("info", "Get Started",
                       "Type a ticker above and click Add to build your portfolio.",
                       "Start with 5\u201310 diversified names."),
            unsafe_allow_html=True,
        )

    divider()
    col_save, col_policy = st.columns(2)
    with col_save:
        if st.button("Save Portfolio", type="primary"):
            db = Database()
            ver = db.save_portfolio(
                portfolio.model_dump_json(), name="default",
                notes=f"Saved from UI at {datetime.utcnow().isoformat()}"
            )
            portfolio.version = ver
            st.session_state.portfolio = portfolio
            AuditLogger().log(AuditAction.PORTFOLIO_COMMITTED, details={"version": ver})
            if "session_decisions" in st.session_state:
                st.session_state.session_decisions += 1
            st.success(f"Portfolio saved (version {ver}).")

    with col_policy:
        with st.expander("Investment Policy Editor"):
            policy.max_position_weight = st.slider("Max position weight", 0.01, 0.30, policy.max_position_weight, 0.01)
            policy.top5_max_concentration = st.slider("Top-5 max concentration", 0.20, 0.80, policy.top5_max_concentration, 0.05)
            policy.sector_cap = st.slider("Sector cap", 0.10, 0.50, policy.sector_cap, 0.05)
            policy.cash_floor = st.slider("Cash floor", 0.0, 0.10, policy.cash_floor, 0.01)
            policy.max_turnover_per_rebalance = st.slider("Max turnover", 0.05, 0.30, policy.max_turnover_per_rebalance, 0.01)

            panel_header("Autopilot Thresholds")
            policy.autopilot.max_weight_delta_auto = st.slider("Auto weight delta limit", 0.005, 0.05, policy.autopilot.max_weight_delta_auto, 0.005)
            policy.autopilot.min_confidence_auto = st.slider("Auto confidence minimum", 0.50, 0.95, policy.autopilot.min_confidence_auto, 0.05)

            if st.button("Save Policy"):
                db = Database()
                db.save_policy("default", policy.model_dump_json())
                st.session_state.policy = policy
                AuditLogger().log(AuditAction.POLICY_CHANGE, details=policy.model_dump(mode="json"))
                st.success("Policy saved.")

# ── Risk Dashboard ────────────────────────────────────────────────────
with tab_risk:
    panel_header("Risk Dashboard")

    if not portfolio.positions:
        st.markdown(alert_card("info", "No Positions", "Add positions in the Builder tab.", ""), unsafe_allow_html=True)
    else:
        engine = ConstraintsEngine(policy)
        alerts = engine.check_portfolio(portfolio)
        weights = [p.weight for p in portfolio.positions]
        sorted_w = sorted(weights, reverse=True)

        render_kpi_row([
            ("Top-5 Concentration", f"{sum(sorted_w[:5]):.1%}",
             "High risk" if sum(sorted_w[:5]) > 0.50 else "Diversified",
             "neg" if sum(sorted_w[:5]) > 0.50 else "pos"),
            ("HHI", f"{sum(w**2 for w in weights):.4f}",
             "Concentrated" if sum(w**2 for w in weights) > 0.10 else "Well spread",
             "neg" if sum(w**2 for w in weights) > 0.10 else "pos"),
            ("Positions", str(len(portfolio.positions)),
             f"Min: {policy.min_positions}", "neutral"),
            ("Alerts", str(len(alerts)),
             "All clear" if not alerts else f"{len(alerts)} issues",
             "pos" if not alerts else "neg"),
        ])

        divider()

        if alerts:
            panel_header("Active Alerts")
            for a in alerts:
                sev = a.rule.severity.value
                st.markdown(
                    alert_card(sev, a.rule.name, a.message,
                               "Immediate action needed" if sev == "critical" else "Review at next rebalance"),
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                alert_card("success", "All Constraints Passing",
                           "Portfolio within all policy limits.", ""),
                unsafe_allow_html=True,
            )

        col_sector, col_weights = st.columns(2)
        with col_sector:
            sector_w: dict[str, float] = {}
            for pos in portfolio.positions:
                s = pos.sector or "Unknown"
                sector_w[s] = sector_w.get(s, 0.0) + pos.weight
            render_donut(list(sector_w.keys()),
                        [round(v * 100, 2) for v in sector_w.values()],
                        title="Sector Allocation", height=260)
        with col_weights:
            tickers = [p.ticker for p in sorted(portfolio.positions, key=lambda x: -x.weight)][:15]
            wts = [portfolio.weight_map[t] * 100 for t in tickers]
            render_hbar(tickers, wts, title="Position Weights (%)", color_by_sign=False, height=280)

# ── Factor Exposures ──────────────────────────────────────────────────
with tab_factors:
    panel_header("Factor Exposure Analysis")

    _FACTOR_INFO = {
        "Mkt-RF": ("Market Risk Premium",
                    "Excess return of the broad stock market over the risk-free rate. "
                    "A beta of 1.0 means you move in lockstep with the market."),
        "SMB": ("Small Minus Big",
                "Return premium of small-cap stocks over large-cap stocks. "
                "Positive = tilted toward smaller companies."),
        "HML": ("High Minus Low (Value)",
                "Return premium of value stocks (cheap, high book-to-market) over "
                "growth stocks. Positive = value tilt, negative = growth tilt."),
        "RMW": ("Robust Minus Weak (Profitability)",
                "Return premium of highly profitable firms over weakly profitable firms. "
                "Positive = portfolio favours quality/profitable companies."),
        "CMA": ("Conservative Minus Aggressive (Investment)",
                "Return premium of firms that invest conservatively over aggressive "
                "spenders. Positive = avoids high-capex companies."),
    }

    model_choice = st.radio("Model", ["FF3 (3-factor)", "FF5 (5-factor)"],
                            horizontal=True, key="ff_model")
    model_type = "FF3" if "3" in model_choice else "FF5"

    # ── Show the regression equation ──
    if model_type == "FF3":
        eq_html = (
            f'<div style="padding:14px 18px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-left:3px solid {ACCENT};border-radius:4px;margin:10px 0;'
            f'font-family:{FONT_MONO};font-size:0.82rem;color:{TEXT_MUTED};line-height:1.8;">'
            f'<span style="color:{TEXT_DIM};font-size:0.65rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;display:block;margin-bottom:6px;">FF3 Regression Equation</span>'
            f'R<sub>portfolio</sub> \u2212 R<sub>f</sub> = '
            f'<span style="color:{ACCENT};">\u03B1</span> + '
            f'<span style="color:{POSITIVE};">\u03B2<sub>mkt</sub></span>(R<sub>mkt</sub> \u2212 R<sub>f</sub>) + '
            f'<span style="color:{WARNING};">\u03B2<sub>smb</sub></span>(SMB) + '
            f'<span style="color:{DANGER};">\u03B2<sub>hml</sub></span>(HML) + \u03B5'
            f'</div>'
        )
    else:
        eq_html = (
            f'<div style="padding:14px 18px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-left:3px solid {ACCENT};border-radius:4px;margin:10px 0;'
            f'font-family:{FONT_MONO};font-size:0.82rem;color:{TEXT_MUTED};line-height:1.8;">'
            f'<span style="color:{TEXT_DIM};font-size:0.65rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;display:block;margin-bottom:6px;">FF5 Regression Equation</span>'
            f'R<sub>portfolio</sub> \u2212 R<sub>f</sub> = '
            f'<span style="color:{ACCENT};">\u03B1</span> + '
            f'<span style="color:{POSITIVE};">\u03B2<sub>mkt</sub></span>(R<sub>mkt</sub> \u2212 R<sub>f</sub>) + '
            f'<span style="color:{WARNING};">\u03B2<sub>smb</sub></span>(SMB) + '
            f'<span style="color:{DANGER};">\u03B2<sub>hml</sub></span>(HML) + '
            f'\u03B2<sub>rmw</sub>(RMW) + '
            f'\u03B2<sub>cma</sub>(CMA) + \u03B5'
            f'</div>'
        )
    st.markdown(eq_html, unsafe_allow_html=True)

    # ── Factor legend ──
    factors_to_show = ["Mkt-RF", "SMB", "HML"] if model_type == "FF3" else list(_FACTOR_INFO.keys())
    with st.expander("What do these factors mean?", expanded=False):
        for fkey in factors_to_show:
            fname, fdesc = _FACTOR_INFO[fkey]
            st.markdown(
                f'<div style="padding:8px 0 8px 12px;border-left:2px solid {ACCENT};'
                f'margin:4px 0;">'
                f'<span style="font-weight:700;font-family:{FONT_MONO};color:{TEXT_PRIMARY};'
                f'font-size:0.84rem;">{fkey}</span> '
                f'<span style="color:{TEXT_DIM};font-size:0.78rem;">({fname})</span><br/>'
                f'<span style="color:{TEXT_MUTED};font-size:0.8rem;">{fdesc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    divider()

    if st.button("Run Factor Regression", key="est_factors", type="primary"):
        with st.spinner("Downloading price data and running OLS regression..."):
            try:
                from quant.factor_model import FamaFrenchModel
                import yfinance as yf

                ff = FamaFrenchModel()
                raw_tickers = [p.ticker for p in portfolio.positions[:20]]
                yf_tickers = [t.replace(".", "-") for t in raw_tickers]
                yf_to_orig = dict(zip(yf_tickers, raw_tickers))

                price_df = yf.download(
                    yf_tickers, period="2y", interval="1d",
                    auto_adjust=True, progress=False,
                )

                if isinstance(price_df.columns, pd.MultiIndex):
                    close = price_df["Close"]
                else:
                    close = price_df[["Close"]].rename(columns={"Close": yf_tickers[0]})

                close = close.rename(columns=yf_to_orig)
                close = close.dropna(how="all")
                missing = [t for t in raw_tickers if t not in close.columns or close[t].isna().all()]
                if missing:
                    st.warning(f"No price data for: {', '.join(missing[:5])}")

                ret_df = close.pct_change().dropna()
                available = [t for t in raw_tickers if t in ret_df.columns]

                if available and len(ret_df) >= 30:
                    w_arr = np.array([portfolio.weight_map.get(t, 0) for t in available])
                    w_sum = w_arr.sum()
                    if w_sum > 0:
                        w_arr = w_arr / w_sum
                    port_ret = (ret_df[available].values * w_arr).sum(axis=1)
                    port_series = pd.Series(port_ret, index=ret_df.index, name="portfolio")

                    exposure = ff.estimate_exposure(port_series, model_type=model_type)
                    st.session_state["factor_exposure"] = exposure.model_dump(mode="json")
                    st.session_state["factor_model_type"] = model_type

                    # Store regression data for plotting
                    import statsmodels.api as sm_api
                    ff_data = ff.get_ff3() if model_type == "FF3" else ff.get_ff5()
                    f_cols = ["Mkt-RF", "SMB", "HML"] if model_type == "FF3" else ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
                    avail = [c for c in f_cols if c in ff_data.columns]
                    merged = pd.DataFrame({"ret": port_series}).join(ff_data[avail + ["RF"]], how="inner").dropna()
                    if len(merged) >= 30:
                        y_exc = merged["ret"] - merged["RF"]
                        X_reg = sm_api.add_constant(merged[avail])
                        ols_fit = sm_api.OLS(y_exc, X_reg).fit()
                        st.session_state["factor_reg_data"] = {
                            "dates": merged.index.strftime("%Y-%m-%d").tolist(),
                            "actual": y_exc.tolist(),
                            "fitted": ols_fit.fittedvalues.tolist(),
                            "residuals": ols_fit.resid.tolist(),
                            "mkt_rf": merged["Mkt-RF"].tolist(),
                        }
                else:
                    st.warning("Insufficient price data for regression.")
            except Exception as e:
                st.error(f"Error: {e}")

    fe = st.session_state.get("factor_exposure")
    if fe:
        fm_type = st.session_state.get("factor_model_type", "FF3")
        obs = fe.get("observations", 0)
        r2 = fe.get("r_squared", 0)
        adj_r2 = fe.get("adj_r_squared", 0)
        alpha_daily = fe.get("alpha", 0)
        alpha_ann = alpha_daily * 252
        alpha_pv = fe.get("alpha_pvalue", 1)
        betas = fe.get("betas", {})
        pvalues = fe.get("beta_pvalues", {})

        # ── Regression summary header ──
        r2_variant = "pos" if r2 > 0.7 else "neutral" if r2 > 0.4 else "neg"
        alpha_variant = "pos" if alpha_ann > 0 and alpha_pv < 0.05 else "neg" if alpha_ann < 0 and alpha_pv < 0.05 else "neutral"
        render_kpi_row([
            ("Model", fm_type, f"{obs} daily observations", "neutral"),
            ("R\u00b2", f"{r2:.4f}",
             f"{r2:.0%} of variance explained", r2_variant),
            ("Adj R\u00b2", f"{adj_r2:.4f}", "", "neutral"),
            ("Alpha (annual)", f"{alpha_ann:+.2%}",
             f"p={alpha_pv:.3f}" + (" \u2714" if alpha_pv < 0.05 else " n.s."), alpha_variant),
        ])

        divider()

        # ── Factor betas — bar chart ──
        if betas:
            import plotly.graph_objects as go
            factor_names = list(betas.keys())
            beta_vals = [betas[f] for f in factor_names]
            colors = [POSITIVE if v > 0 else DANGER for v in beta_vals]

            fig = go.Figure(go.Bar(
                x=beta_vals, y=factor_names, orientation="h",
                marker_color=colors,
                text=[f"{v:+.3f}" for v in beta_vals],
                textposition="outside",
                textfont=dict(family="JetBrains Mono, monospace", size=11),
            ))
            fig.update_layout(
                height=45 * len(factor_names) + 60,
                **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
                xaxis=dict(zeroline=True, zerolinecolor=BORDER, zerolinewidth=2,
                           gridcolor=BORDER, title="Beta coefficient"),
                yaxis=dict(gridcolor=BORDER),
                title=dict(text="Factor Beta Loadings",
                           font=dict(size=12, family="Inter", color=TEXT_MUTED)),
            )
            st.plotly_chart(fig, use_container_width=True)

            divider()

            # ── Regression scatter plots ──
            reg_data = st.session_state.get("factor_reg_data")
            if reg_data:
                st.markdown(
                    f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;'
                    f'color:{TEXT_DIM};font-weight:600;margin-bottom:4px;">Regression Diagnostics</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:0.76rem;color:{TEXT_MUTED};padding:10px 14px;'
                    f'background:{BG_PANEL};border:1px solid {BORDER};border-radius:6px;'
                    f'margin-bottom:16px;line-height:1.7;">'
                    f'<strong style="color:{TEXT_PRIMARY};">Where the data comes from:</strong> '
                    f'The <strong>Y-axis (Actual)</strong> is your portfolio\'s daily excess return '
                    f'(weighted-average daily price change of your holdings from '
                    f'<span style="color:{ACCENT};">Yahoo Finance</span>, minus the daily risk-free rate). '
                    f'The <strong>X-axis</strong> uses factor return data from the '
                    f'<span style="color:{ACCENT};">Kenneth French Data Library</span> '
                    f'(academic benchmark published by Dartmouth). '
                    f'None of these come from company financials (income statements, balance sheets) '
                    f'\u2014 they are purely based on <em>daily stock price movements</em> '
                    f'and how those movements co-vary with systematic market factors.</div>',
                    unsafe_allow_html=True,
                )

                actual = reg_data["actual"]
                fitted = reg_data["fitted"]
                residuals = reg_data["residuals"]
                mkt_rf = reg_data["mkt_rf"]
                dates = reg_data["dates"]
                n_obs = len(actual)

                col_scatter1, col_scatter2 = st.columns(2)

                with col_scatter1:
                    fig_av = go.Figure()
                    fig_av.add_trace(go.Scatter(
                        x=fitted, y=actual, mode="markers",
                        marker=dict(size=4, color=ACCENT, opacity=0.5),
                        name="Daily returns",
                        hovertemplate="Predicted: %{x:.4f}<br>Actual: %{y:.4f}<extra></extra>",
                    ))
                    mn_val = min(min(fitted), min(actual))
                    mx_val = max(max(fitted), max(actual))
                    fig_av.add_trace(go.Scatter(
                        x=[mn_val, mx_val], y=[mn_val, mx_val],
                        mode="lines", line=dict(color=DANGER, dash="dash", width=1.5),
                        name="Perfect fit (45°)",
                    ))
                    fig_av.update_layout(
                        title=dict(text="Actual vs Predicted Excess Returns",
                                   font=dict(size=12, family="Inter", color=TEXT_MUTED)),
                        height=370,
                        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
                        xaxis=dict(title="Predicted (from factor model)", gridcolor=BORDER,
                                   zeroline=True, zerolinecolor=BORDER),
                        yaxis=dict(title="Actual (portfolio price returns)", gridcolor=BORDER,
                                   zeroline=True, zerolinecolor=BORDER),
                        showlegend=True,
                        legend=dict(font=dict(size=9, color=TEXT_DIM), bgcolor="rgba(0,0,0,0)"),
                    )
                    st.plotly_chart(fig_av, use_container_width=True)
                    st.markdown(
                        f'<div style="font-size:0.74rem;color:{TEXT_MUTED};padding:8px 12px;'
                        f'background:{BG_CARD};border:1px solid {BORDER};border-radius:4px;line-height:1.65;">'
                        f'<strong style="color:{TEXT_PRIMARY};">How to read this:</strong> Each dot = one trading day ({n_obs} days total). '
                        f'<strong>X-axis (Predicted)</strong> = the return the {fm_type} model says your portfolio '
                        f'<em>should</em> have earned that day, based on how the market factors (Mkt-RF, SMB, HML'
                        f'{", RMW, CMA" if fm_type == "FF5" else ""}) moved. '
                        f'<strong>Y-axis (Actual)</strong> = what your portfolio <em>actually</em> returned '
                        f'(from stock price changes via yfinance). '
                        f'The <span style="color:{DANGER};">dashed red line</span> = perfect prediction. '
                        f'Dots tight around the line = the factor model explains your returns well. '
                        f'Scatter = idiosyncratic risk (stock-specific events the model can\'t capture).</div>',
                        unsafe_allow_html=True,
                    )

                with col_scatter2:
                    fig_mkt = go.Figure()
                    fig_mkt.add_trace(go.Scatter(
                        x=mkt_rf, y=actual, mode="markers",
                        marker=dict(size=4, color=ACCENT, opacity=0.5),
                        name="Daily returns",
                        hovertemplate="Mkt-RF: %{x:.4f}<br>Portfolio: %{y:.4f}<extra></extra>",
                    ))
                    mkt_beta = betas.get("Mkt-RF", 1.0)
                    mkt_alpha = fe.get("alpha", 0)
                    x_sorted = sorted(mkt_rf)
                    x_line = [x_sorted[0], x_sorted[-1]]
                    y_line = [mkt_alpha + mkt_beta * x for x in x_line]
                    fig_mkt.add_trace(go.Scatter(
                        x=x_line, y=y_line,
                        mode="lines", line=dict(color=POSITIVE, width=2),
                        name=f"Regression (β={mkt_beta:.3f})",
                    ))
                    fig_mkt.update_layout(
                        title=dict(text="Portfolio Returns vs Market Returns",
                                   font=dict(size=12, family="Inter", color=TEXT_MUTED)),
                        height=370,
                        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
                        xaxis=dict(title="Market excess return (Mkt-RF, French Library)", gridcolor=BORDER,
                                   zeroline=True, zerolinecolor=BORDER),
                        yaxis=dict(title="Portfolio excess return (yfinance prices)", gridcolor=BORDER,
                                   zeroline=True, zerolinecolor=BORDER),
                        showlegend=True,
                        legend=dict(font=dict(size=9, color=TEXT_DIM), bgcolor="rgba(0,0,0,0)"),
                    )
                    st.plotly_chart(fig_mkt, use_container_width=True)
                    st.markdown(
                        f'<div style="font-size:0.74rem;color:{TEXT_MUTED};padding:8px 12px;'
                        f'background:{BG_CARD};border:1px solid {BORDER};border-radius:4px;line-height:1.65;">'
                        f'<strong style="color:{TEXT_PRIMARY};">How to read this:</strong> '
                        f'This isolates the single most important factor: the broad market. '
                        f'<strong>X-axis</strong> = daily market excess return (total US market return minus '
                        f'T-bill rate, from the <span style="color:{ACCENT};">Kenneth French Library</span>). '
                        f'<strong>Y-axis</strong> = your portfolio\'s excess return that same day '
                        f'(from <span style="color:{ACCENT};">yfinance</span> stock prices). '
                        f'The <span style="color:{POSITIVE};">green regression line</span> has '
                        f'slope = <strong>{mkt_beta:+.3f}</strong> (market beta \u2014 if market rises 1%, '
                        f'your portfolio moves ~{abs(mkt_beta):.1%}) and '
                        f'intercept = <strong>{mkt_alpha:+.5f}</strong> (daily alpha).</div>',
                        unsafe_allow_html=True,
                    )

                # ── Residuals over time ──
                fig_resid = go.Figure()
                fig_resid.add_trace(go.Scatter(
                    x=dates, y=residuals, mode="lines",
                    line=dict(color=ACCENT, width=1),
                    fill="tozeroy",
                    fillcolor=f"rgba(91,155,213,0.1)",
                    name="Residual",
                    hovertemplate="%{x}<br>Residual: %{y:.4f}<extra></extra>",
                ))
                fig_resid.add_hline(y=0, line_dash="dash", line_color=TEXT_DIM, line_width=1)
                fig_resid.update_layout(
                    title=dict(text="Regression Residuals Over Time (What Factors Can't Explain)",
                               font=dict(size=12, family="Inter", color=TEXT_MUTED)),
                    height=250,
                    **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
                    xaxis=dict(gridcolor=BORDER, type="date"),
                    yaxis=dict(title="Residual (actual \u2212 predicted)", gridcolor=BORDER,
                               zeroline=True, zerolinecolor=BORDER),
                    showlegend=False,
                )
                st.plotly_chart(fig_resid, use_container_width=True)
                st.markdown(
                    f'<div style="font-size:0.74rem;color:{TEXT_MUTED};padding:8px 12px;'
                    f'background:{BG_CARD};border:1px solid {BORDER};border-radius:4px;line-height:1.65;">'
                    f'<strong style="color:{TEXT_PRIMARY};">How to read this:</strong> '
                    f'Residuals = Actual return \u2212 Predicted return, for each trading day. '
                    f'This is the portion of your portfolio\'s performance that the {fm_type} factors '
                    f'<em>cannot</em> explain \u2014 driven by stock-specific events like earnings surprises, '
                    f'product launches, management changes, or sector rotation not captured by the factors. '
                    f'Ideally this looks like random noise around zero. '
                    f'If you see persistent positive spikes = your stock picks are adding value beyond factor exposure. '
                    f'Persistent negative = holdings are dragging performance for reasons outside systematic risk.</div>',
                    unsafe_allow_html=True,
                )

                divider()

            # ── Per-factor detail cards ──
            st.markdown(
                f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;'
                f'color:{TEXT_DIM};font-weight:600;margin-bottom:8px;">Factor-by-Factor Breakdown</div>',
                unsafe_allow_html=True,
            )

            for factor in factor_names:
                beta = betas[factor]
                pv = pvalues.get(factor, 1)
                sig = pv < 0.05
                fname, fdesc = _FACTOR_INFO.get(factor, (factor, ""))

                sig_badge = (
                    f'<span style="padding:2px 6px;border-radius:3px;font-size:0.65rem;'
                    f'font-weight:700;background:{"rgba(74,222,128,0.15)" if sig else "rgba(107,114,128,0.15)"};'
                    f'color:{POSITIVE if sig else TEXT_DIM};">{"SIGNIFICANT" if sig else "NOT SIGNIFICANT"}</span>'
                )

                if factor == "Mkt-RF":
                    if beta > 1.1:
                        reading = "Portfolio is more volatile than the market (aggressive)."
                    elif beta < 0.9:
                        reading = "Portfolio is less volatile than the market (defensive)."
                    else:
                        reading = "Portfolio moves roughly in line with the market."
                elif factor == "SMB":
                    if beta > 0.1:
                        reading = "Tilted toward small-cap stocks."
                    elif beta < -0.1:
                        reading = "Tilted toward large-cap stocks."
                    else:
                        reading = "Neutral size exposure."
                elif factor == "HML":
                    if beta > 0.1:
                        reading = "Tilted toward value stocks (cheap, high book-to-market)."
                    elif beta < -0.1:
                        reading = "Tilted toward growth stocks (expensive, high multiples)."
                    else:
                        reading = "Neutral value/growth exposure."
                elif factor == "RMW":
                    if beta > 0.1:
                        reading = "Favours highly profitable, quality companies."
                    elif beta < -0.1:
                        reading = "Exposed to less profitable companies."
                    else:
                        reading = "Neutral profitability exposure."
                elif factor == "CMA":
                    if beta > 0.1:
                        reading = "Favours conservative (low investment) firms."
                    elif beta < -0.1:
                        reading = "Exposed to aggressive (high capex) companies."
                    else:
                        reading = "Neutral investment-style exposure."
                else:
                    reading = ""

                beta_color = POSITIVE if beta > 0 else DANGER if beta < 0 else TEXT_DIM

                st.markdown(
                    f'<div style="padding:12px 16px;background:{BG_CARD};border:1px solid {BORDER};'
                    f'border-radius:4px;margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<span style="font-weight:700;font-family:{FONT_MONO};color:{TEXT_PRIMARY};'
                    f'font-size:0.9rem;">{factor}</span> '
                    f'<span style="color:{TEXT_DIM};font-size:0.75rem;">({fname})</span>'
                    f'</div>'
                    f'<div style="display:flex;gap:10px;align-items:center;">'
                    f'{sig_badge}'
                    f'<span style="font-family:{FONT_MONO};font-size:1.1rem;font-weight:800;'
                    f'color:{beta_color};">{beta:+.4f}</span>'
                    f'</div></div>'
                    f'<div style="margin-top:6px;font-size:0.8rem;color:{TEXT_MUTED};">'
                    f'{reading}</div>'
                    f'<div style="margin-top:4px;font-size:0.72rem;color:{TEXT_DIM};">'
                    f'p-value: {pv:.4f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        divider()

        # ── Alpha interpretation ──
        alpha_sig = alpha_pv < 0.05
        if alpha_sig and alpha_ann > 0:
            alpha_reading = (
                f"The portfolio generates a statistically significant annualised alpha of "
                f"{alpha_ann:+.2%} (p={alpha_pv:.4f}). This suggests return generation beyond "
                f"what the factor exposures explain \u2014 potentially attributable to stock "
                f"selection skill or an unmeasured factor."
            )
            alpha_sev = "success"
        elif alpha_sig and alpha_ann < 0:
            alpha_reading = (
                f"The portfolio has a statistically significant negative alpha of "
                f"{alpha_ann:+.2%} (p={alpha_pv:.4f}). After controlling for factor exposures, "
                f"the portfolio underperforms \u2014 review holdings for drag."
            )
            alpha_sev = "critical"
        else:
            alpha_reading = (
                f"Alpha is {alpha_ann:+.2%} but not statistically significant (p={alpha_pv:.4f}). "
                f"The portfolio's returns are largely explained by its factor exposures \u2014 "
                f"there is no evidence of excess return beyond systematic risk."
            )
            alpha_sev = "info"

        st.markdown(
            alert_card(alpha_sev, "Alpha Interpretation", alpha_reading,
                       f"R\u00b2 = {r2:.4f} \u2014 {r2:.0%} of portfolio variance explained by {fm_type} factors"),
            unsafe_allow_html=True,
        )

        # ── R-squared interpretation ──
        if r2 > 0.8:
            r2_reading = (
                f"R\u00b2 of {r2:.4f} indicates the {fm_type} factors explain {r2:.0%} of portfolio "
                f"variance. This is a high fit \u2014 the portfolio's behaviour is well-captured "
                f"by systematic risk factors."
            )
        elif r2 > 0.5:
            r2_reading = (
                f"R\u00b2 of {r2:.4f} means {r2:.0%} of variance is explained. Moderate fit \u2014 "
                f"some idiosyncratic stock-specific risk is present beyond the factor model."
            )
        else:
            r2_reading = (
                f"R\u00b2 of {r2:.4f} is low \u2014 only {r2:.0%} of variance explained. The portfolio "
                f"has significant idiosyncratic risk not captured by {fm_type} factors."
            )

        st.markdown(
            f'<div style="padding:12px 16px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-left:3px solid {ACCENT};border-radius:4px;margin:8px 0;'
            f'font-size:0.82rem;color:{TEXT_MUTED};line-height:1.6;">'
            f'<span style="color:{TEXT_DIM};font-size:0.65rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;display:block;margin-bottom:4px;">Model Fit</span>'
            f'{r2_reading}</div>',
            unsafe_allow_html=True,
        )

# ── Rebalance & Autopilot ────────────────────────────────────────────
with tab_rebalance:
    panel_header("Rebalance & Hybrid Autopilot")

    _rebal_msg = st.session_state.pop("_rebalance_msg", None)
    if _rebal_msg:
        st.markdown(
            alert_card("success", "Portfolio Updated", _rebal_msg,
                       "All changes saved to database and audit trail."),
            unsafe_allow_html=True,
        )

    autopilot_mode = st.session_state.get("autopilot_mode", "hybrid")
    kill_active = st.session_state.get("kill_switch", False)

    if kill_active:
        st.markdown(
            alert_card("critical", "Kill Switch Active",
                       "All automated actions halted. Disable in sidebar.",
                       "Safety control \u2014 no trades will execute."),
            unsafe_allow_html=True,
        )

    mode_labels = {"full_manual": "Manual", "hybrid": "Hybrid", "full_auto": "Auto"}
    st.markdown(
        f'<span style="font-size:0.8rem;color:{TEXT_DIM};">Mode:</span> '
        f'{badge(mode_labels.get(autopilot_mode, autopilot_mode), "paper")}',
        unsafe_allow_html=True,
    )

    if st.button("Generate AI Rebalance Proposal", key="run_rebalance", type="primary"):
        with st.spinner("Asset Manager Agent analyzing..."):
            try:
                from agents.asset_manager import AssetManagerAgent
                from mcp_servers.alpha_vantage import AlphaVantageMCP
                from mcp_servers.fred import FredMCP
                from mcp_servers.gdelt import GdeltMCP
                from mcp_servers.quant_mcp import QuantMCP

                agent = AssetManagerAgent()
                agent.register_tool("mcp_quant", QuantMCP())
                agent.register_tool("mcp_marketdata_alpha_vantage", AlphaVantageMCP())
                agent.register_tool("mcp_news_gdelt", GdeltMCP())
                agent.register_tool("mcp_macro_fred", FredMCP())

                result = agent.run({
                    "portfolio": portfolio.model_dump(mode="json"),
                    "policy": policy.model_dump(mode="json"),
                })

                plan = TradePlan.model_validate(result)
                validator = AutopilotValidator(policy)
                plan = validator.classify_plan(plan, AutopilotMode(autopilot_mode))
                st.session_state["trade_plan"] = plan.model_dump(mode="json")
            except Exception as e:
                st.error(f"Error: {e}")

    plan_data = st.session_state.get("trade_plan")
    if plan_data:
        plan = TradePlan.model_validate(plan_data)

        render_kpi_row([
            ("Turnover", f"{plan.total_turnover:.1%}", "", "neutral"),
            ("Auto Actions", str(len(plan.auto_actions)), "", "pos"),
            ("Review Actions", str(len(plan.review_actions)), "",
             "neg" if plan.review_actions else "neutral"),
        ])

        st.markdown(f"**Rationale:** {plan.rationale_summary}")
        divider()

        if plan.auto_actions:
            st.markdown(
                alert_card("success", f"AUTO Bucket \u2014 {len(plan.auto_actions)} action(s)",
                           "Meet all safety criteria \u2014 will auto-apply.",
                           "Low risk: small deltas, no new positions, high confidence"),
                unsafe_allow_html=True,
            )
            for a in plan.auto_actions:
                st.markdown(
                    f'<span style="font-family:{FONT_MONO};font-size:0.82rem;color:{TEXT_MUTED};">'
                    f'`{a.action.value}` <strong style="color:{TEXT_PRIMARY};">{a.ticker}</strong> '
                    f'D={a.weight_delta:+.1%} \u2192 {a.target_weight:.1%} '
                    f'{confidence_badge_html(a.confidence)}</span>',
                    unsafe_allow_html=True,
                )

        if plan.review_actions:
            st.markdown(
                alert_card("warning", f"REVIEW Bucket \u2014 {len(plan.review_actions)} action(s)",
                           "Require explicit approval before execution.",
                           "Check each action and approve or reject"),
                unsafe_allow_html=True,
            )
            selected = {}
            for i, a in enumerate(plan.review_actions):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f'<span style="font-family:{FONT_MONO};font-size:0.82rem;">'
                        f'<strong style="color:{TEXT_PRIMARY};">{a.ticker}</strong> \u2014 '
                        f'`{a.action.value}` D={a.weight_delta:+.1%} \u2192 {a.target_weight:.1%}</span>',
                        unsafe_allow_html=True,
                    )
                    if a.rationale:
                        st.caption(a.rationale)
                    confidence_bar(a.confidence, "Action Confidence")
                    if a.news_risk_flags:
                        st.markdown(
                            alert_card("warning", "News Risk", ", ".join(a.news_risk_flags), ""),
                            unsafe_allow_html=True,
                        )
                with col2:
                    selected[i] = st.checkbox("Approve", key=f"approve_{i}")

        divider()

        pm_note = st.text_area("PM Rationale (required for approvals)",
                               placeholder="Why are you approving these actions?",
                               key="pm_note")

        col_approve, col_reject = st.columns(2)
        with col_approve:
            if st.button("Apply Approved Actions", key="apply_approved", type="primary"):
                if kill_active:
                    st.error("Kill switch active.")
                elif not pm_note.strip():
                    st.warning("PM rationale is required.")
                else:
                    audit = AuditLogger()
                    approved_indices = [i for i, ok in selected.items() if ok] if plan.review_actions else []
                    approved_actions = [plan.review_actions[i] for i in approved_indices]
                    all_actions = plan.auto_actions + approved_actions

                    for action in approved_actions:
                        audit.log(AuditAction.TRADE_APPROVED, ticker=action.ticker,
                                  details=action.model_dump(mode="json"), pm_rationale=pm_note)

                    for action in all_actions:
                        existing = {p.ticker: p for p in portfolio.positions}
                        if action.ticker in existing:
                            existing[action.ticker].weight = action.target_weight
                        elif action.is_new_position:
                            existing[action.ticker] = Position(ticker=action.ticker, weight=action.target_weight)
                        if action.is_full_exit and action.ticker in existing:
                            del existing[action.ticker]
                        portfolio.positions = list(existing.values())

                    portfolio.cash_weight = max(0, 1.0 - sum(p.weight for p in portfolio.positions))
                    db = Database()
                    ver = db.save_portfolio(portfolio.model_dump_json(), notes=pm_note)
                    portfolio.version = ver
                    st.session_state.portfolio = portfolio
                    if "session_decisions" in st.session_state:
                        st.session_state.session_decisions += 1
                    audit.log(AuditAction.PORTFOLIO_COMMITTED,
                              details={"version": ver, "actions": len(all_actions)}, pm_rationale=pm_note)
                    st.session_state.pop("trade_plan", None)
                    st.session_state["_rebalance_msg"] = (
                        f"Applied {len(all_actions)} action(s). "
                        f"Portfolio updated to v{ver}. "
                        f"Switch to the Builder tab to see updated positions."
                    )
                    st.rerun()

        with col_reject:
            if st.button("Reject All", key="reject_all"):
                AuditLogger().log(AuditAction.TRADE_REJECTED,
                                  details={"plan": "rejected"}, pm_rationale=pm_note or "Rejected")
                st.session_state.pop("trade_plan", None)
                st.session_state["_rebalance_msg"] = "Trade plan rejected and logged."
                st.rerun()

# ── Stress Testing ────────────────────────────────────────────────────
with tab_stress:
    panel_header("Portfolio Stress Testing")

    if not portfolio.positions:
        st.markdown(alert_card("info", "No Positions", "Add positions first.", ""), unsafe_allow_html=True)
    else:
        if st.button("Run All Stress Scenarios", key="run_stress", type="primary"):
            results = StressTestEngine.run_all_scenarios(portfolio)
            st.session_state["stress_results"] = [
                {"name": r.scenario_name, "impact": round(r.portfolio_impact_pct, 2),
                 "desc": r.description, "contributors": r.top_contributors}
                for r in results
            ]

        stress = st.session_state.get("stress_results")
        if stress:
            render_hbar(
                [s["name"] for s in stress],
                [s["impact"] for s in stress],
                title="Portfolio Impact by Scenario (%)",
                height=280,
            )

            for s in stress:
                with st.expander(f'{s["name"]} \u2014 {s["impact"]:+.2f}%'):
                    st.write(s["desc"])
                    if s["contributors"]:
                        panel_header("Top loss contributors")
                        for t, v in s["contributors"]:
                            st.markdown(
                                f'<span style="font-family:{FONT_MONO};font-size:0.82rem;">'
                                f'{t}: <span style="color:{DANGER if v < 0 else POSITIVE};">{v:+.2f}%</span></span>',
                                unsafe_allow_html=True,
                            )

# ── Investment Committee ──────────────────────────────────────────────
with tab_committee:

    AGENT_PERSONAS = {
        "Market Strategist": {
            "icon": "globe",
            "color": "#38bdf8",
            "scope": "macro regime, rates, inflation, geopolitical risk, market sentiment, economic indicators",
        },
        "Equity Analyst": {
            "icon": "search",
            "color": POSITIVE,
            "scope": "stock-level thesis, earnings, valuation, catalysts, company fundamentals, sector analysis",
        },
        "Risk Manager": {
            "icon": "shield",
            "color": DANGER,
            "scope": "portfolio risk, drawdown, correlation, concentration, VaR, stress tests, tail risk",
        },
        "Asset Manager": {
            "icon": "bar-chart",
            "color": WARNING,
            "scope": "trade plan, position sizing, rebalancing, portfolio construction, allocation strategy",
        },
        "Committee Chair": {
            "icon": "award",
            "color": ACCENT,
            "scope": "synthesis, final decision, assumptions, dissenting views, meta-discussion, governance",
        },
    }

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:{POSITIVE};'
        f'box-shadow:0 0 8px {POSITIVE};animation:pulse 2s infinite;"></div>'
        f'<span style="font-size:1.05rem;font-weight:700;color:{TEXT_PRIMARY};">'
        f'Investment Committee Debate Room</span>'
        f'<span style="font-size:0.7rem;color:{TEXT_DIM};margin-left:auto;'
        f'font-family:{FONT_MONO};background:{BG_PANEL};padding:3px 8px;border-radius:4px;'
        f'border:1px solid {BORDER};">LIVE SESSION</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Agent panel chips ─────────────────────────────────────────────
    def _to_rgb(hx: str) -> str:
        h = hx.lstrip("#")
        return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"

    chips_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 16px;">'
    for name, p in AGENT_PERSONAS.items():
        rgb = _to_rgb(p["color"])
        chips_html += (
            f'<div style="display:inline-flex;align-items:center;gap:5px;'
            f'padding:4px 10px;border-radius:20px;font-size:0.68rem;font-weight:600;'
            f'color:{p["color"]};background:rgba({rgb},0.08);'
            f'border:1px solid rgba({rgb},0.2);'
            f'font-family:{FONT_MONO};letter-spacing:0.03em;">'
            f'<span style="width:6px;height:6px;border-radius:50%;background:{p["color"]};'
            f'display:inline-block;"></span>'
            f'{name}</div>'
        )
    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin-bottom:20px;'
        f'padding:12px 16px;background:{BG_PANEL};border:1px solid {BORDER};border-radius:6px;'
        f'line-height:1.6;">'
        f'Ask any investment question and the relevant committee member responds automatically. '
        f'Challenge decisions, explore scenarios, question assumptions, or request analysis on specific tickers. '
        f'Your portfolio context is included in every response.</div>',
        unsafe_allow_html=True,
    )

    divider()

    # ── Session state ─────────────────────────────────────────────────
    if "committee_chat" not in st.session_state:
        st.session_state.committee_chat = []

    def _pick_responder(question: str) -> str:
        q = question.lower()
        if any(w in q for w in [
            "macro", "regime", "rate", "inflation", "fed", "gdp",
            "geopolit", "bond", "yield", "economy", "recession",
            "growth", "employment", "cpi", "pce", "treasury",
        ]):
            return "Market Strategist"
        if any(w in q for w in [
            "earning", "valuation", "revenue", "eps", "p/e", "thesis",
            "bull", "bear", "catalyst", "fundamental", "margin", "guidance",
            "sector", "stock", "company", "ticker", "aapl", "msft", "goog",
            "amzn", "nvda", "tsla", "meta",
        ]):
            return "Equity Analyst"
        if any(w in q for w in [
            "risk", "drawdown", "var", "volatil", "correlation", "stress",
            "concentrat", "hedge", "downside", "exposure", "tail", "beta",
            "sharpe", "sortino", "max loss",
        ]):
            return "Risk Manager"
        if any(w in q for w in [
            "trade", "position", "size", "weight", "rebalanc", "allocat",
            "buy", "sell", "trim", "add", "reduce", "overweight", "underweight",
            "cash", "exit", "entry",
        ]):
            return "Asset Manager"
        return "Committee Chair"

    def _build_portfolio_context() -> str:
        """Build context from the current portfolio state."""
        parts = []
        p = portfolio
        cash_val = p.cash_weight * p.total_value
        parts.append(f"PORTFOLIO: {p.name} | Cash: ${cash_val:,.0f} ({p.cash_weight:.1%}) | Total: ${p.total_value:,.0f}")
        if p.positions:
            pos_lines = []
            for pos in p.positions:
                val = pos.shares * pos.current_price
                pos_lines.append(f"  {pos.ticker}: {pos.shares} shares @ ${pos.current_price:.2f} = ${val:,.0f} (w={pos.weight:.1%})")
            parts.append("POSITIONS:\n" + "\n".join(pos_lines))
        pol = policy
        parts.append(f"POLICY: max_position={pol.max_position_weight:.0%}, max_sector={pol.sector_cap:.0%}, "
                      f"cash_floor={pol.cash_floor:.0%}")
        return "\n".join(parts)

    def _build_full_context() -> str:
        """Combine portfolio + any prior committee results into LLM context."""
        ctx = _build_portfolio_context()
        prior = st.session_state.get("committee_results")
        if prior:
            syn = prior.get("synthesis", {})
            ctx += f"\n\nPRIOR COMMITTEE SESSION:"
            ctx += f"\n  VOTE: {syn.get('vote','hold').upper()}"
            ctx += f"\n  CONFIDENCE: {syn.get('confidence',0):.0%}"
            ctx += f"\n  DECISION: {syn.get('decision_note','')[:400]}"
            ctx += f"\n  ASSUMPTIONS: {json.dumps(syn.get('key_assumptions',[]))}"
            mn = prior.get("market_narrative", {})
            if mn:
                ctx += f"\n  MARKET NARRATIVE: {json.dumps(mn, default=str)[:600]}"
            eq = prior.get("equity_theses", {})
            if eq:
                ctx += f"\n  EQUITY THESES: {json.dumps(eq, default=str)[:800]}"
            ra = prior.get("risk_assessment", {})
            if ra:
                ctx += f"\n  RISK ASSESSMENT: {json.dumps(ra, default=str)[:600]}"
            tp = prior.get("trade_plan", {})
            if tp:
                ctx += f"\n  TRADE PLAN: {json.dumps(tp, default=str)[:600]}"
        return ctx

    def _call_committee_llm(question: str, responder: str, history: list[dict], context: str) -> str:
        from config import settings
        persona = AGENT_PERSONAS[responder]
        system = (
            f"You are the {responder} on an institutional investment committee. "
            f"Your domain of expertise: {persona['scope']}.\n\n"
            f"You are in a live debate session with a portfolio manager. "
            f"The portfolio context and any prior committee analysis is provided below.\n\n"
            f"Rules:\n"
            f"- Be direct, specific, and data-driven.\n"
            f"- Reference concrete numbers from the portfolio or analysis when relevant.\n"
            f"- Keep responses focused: 3-6 sentences for quick questions, more for deep dives.\n"
            f"- If asked about something outside your domain, give your perspective but note "
            f"which committee member is better suited.\n"
            f"- You may disagree with the user or other agents — institutional debate is encouraged.\n"
            f"- Never give direct buy/sell recommendations — frame as analysis and considerations."
        )
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"CONTEXT:\n{context}"},
            {"role": "assistant", "content": f"Understood. I'm the {responder}, ready for the debate. What would you like to discuss?"},
        ]
        for msg in history[-12:]:
            role = msg["role"]
            content = msg["content"]
            if role == "assistant":
                resp_name = msg.get("responder", "Committee Chair")
                content = f"[{resp_name}]: {content}"
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        try:
            if settings.use_azure:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                )
                kwargs: dict = {"model": settings.AZURE_OPENAI_DEPLOYMENT, "messages": messages}
                if settings.AZURE_OPENAI_DEPLOYMENT.startswith("o"):
                    kwargs["max_completion_tokens"] = 2048
                else:
                    kwargs["temperature"] = 0.4
                    kwargs["max_tokens"] = 2048
                resp = client.chat.completions.create(**kwargs)
            else:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=settings.LLM_MODEL, messages=messages,
                    temperature=0.4, max_tokens=2048,
                )
            return resp.choices[0].message.content or "No response generated."
        except Exception as e:
            return f"LLM unavailable: {e}"

    # ── Chat history display ──────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        if not st.session_state.committee_chat:
            st.markdown(
                f'<div style="text-align:center;padding:40px 20px;color:{TEXT_DIM};">'
                f'<div style="font-size:1.8rem;margin-bottom:12px;">&#128172;</div>'
                f'<div style="font-size:0.85rem;font-weight:500;color:{TEXT_MUTED};margin-bottom:8px;">'
                f'Start the debate</div>'
                f'<div style="font-size:0.75rem;color:{TEXT_DIM};line-height:1.6;max-width:500px;margin:0 auto;">'
                f'Try: "Should I increase my AAPL position?" &bull; '
                f'"What are the biggest risks in my portfolio?" &bull; '
                f'"Walk me through the macro outlook" &bull; '
                f'"Is my portfolio too concentrated?"</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.committee_chat:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(msg["content"])
                else:
                    responder_name = msg.get("responder", "Committee Chair")
                    persona = AGENT_PERSONAS.get(responder_name, AGENT_PERSONAS["Committee Chair"])
                    with st.chat_message("assistant"):
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">'
                            f'<span style="width:7px;height:7px;border-radius:50%;'
                            f'background:{persona["color"]};display:inline-block;"></span>'
                            f'<span style="font-size:0.72rem;font-weight:700;color:{persona["color"]};'
                            f'letter-spacing:0.04em;text-transform:uppercase;'
                            f'font-family:{FONT_MONO};">{responder_name}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(msg["content"])

    # ── Clear chat button ─────────────────────────────────────────────
    if st.session_state.committee_chat:
        col_clear, col_spacer = st.columns([1, 5])
        with col_clear:
            if st.button("Clear Conversation", key="clear_debate", type="secondary"):
                st.session_state.committee_chat = []
                st.rerun()

    # ── Chat input ────────────────────────────────────────────────────
    user_question = st.chat_input(
        "Ask the committee — e.g. 'Should I increase NVDA?' or 'What's the biggest risk right now?'",
        key="committee_debate_input",
    )

    if user_question:
        st.session_state.committee_chat.append({"role": "user", "content": user_question})

        responder = _pick_responder(user_question)
        context_str = _build_full_context()

        with st.spinner(f"{responder} is responding..."):
            answer = _call_committee_llm(
                user_question, responder,
                st.session_state.committee_chat, context_str,
            )

        st.session_state.committee_chat.append({
            "role": "assistant",
            "content": answer,
            "responder": responder,
        })
        st.rerun()

    # ── Collapsible: Run Full Committee Pipeline ──────────────────────
    divider()
    with st.expander("Run Full Committee Pipeline (optional deep analysis)"):
        st.markdown(
            f'<div style="font-size:0.75rem;color:{TEXT_DIM};margin-bottom:12px;">'
            f'Runs the full 7-step agent pipeline: Market Narrative → Equity Analysis → '
            f'Challenge → Scenario → Risk → Trade Plan → Synthesis. '
            f'Results will enrich subsequent debate responses.</div>',
            unsafe_allow_html=True,
        )
        tickers_input = st.text_input(
            "Tickers (comma-separated)",
            value=",".join(p.ticker for p in portfolio.positions[:5]),
            key="committee_tickers",
        )
        challenge = st.text_area(
            "Challenge for analysis",
            value="Stress test under risk-off regime with rates rising 200bp",
            height=60,
            key="committee_challenge",
        )

        if st.button("Run Full Pipeline", key="run_committee", type="primary"):
            tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
            if not tickers:
                st.warning("Enter at least one ticker.")
            else:
                steps = [
                    ("Market Regime", "active"), ("Equity Analysis", "pending"),
                    ("Challenge", "pending"), ("Risk Update", "pending"),
                    ("Trade Plan", "pending"), ("Synthesis", "pending"),
                ]
                step_container = st.empty()
                with step_container:
                    render_workflow_steps(steps, 0)

                step_n = {"n": 0}
                def progress_cb(msg: str) -> None:
                    step_n["n"] += 1
                    updated = []
                    for i, (name, _) in enumerate(steps):
                        if i < step_n["n"]:
                            updated.append((name, "done"))
                        elif i == step_n["n"]:
                            updated.append((name, "active"))
                        else:
                            updated.append((name, "pending"))
                    with step_container:
                        render_workflow_steps(updated, step_n["n"])

                with st.spinner("Running full investment committee..."):
                    try:
                        from agents.orchestrator import run_investment_committee
                        pipe_results = run_investment_committee(
                            tickers=tickers,
                            portfolio=portfolio.model_dump(mode="json"),
                            policy=policy.model_dump(mode="json"),
                            challenge=challenge,
                            progress_callback=progress_cb,
                        )
                        st.session_state.committee_results = pipe_results
                        with step_container:
                            render_workflow_steps([(n, "done") for n, _ in steps], len(steps))

                        syn = pipe_results.get("synthesis", {})
                        vote = syn.get("vote", "hold")
                        st.markdown(
                            f'<div style="padding:16px;background:{BG_CARD};border:1px solid {BORDER};'
                            f'border-radius:8px;margin-top:12px;">'
                            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
                            f'{vote_badge(vote)}'
                            f'<span style="font-size:0.78rem;color:{TEXT_MUTED};">'
                            f'Confidence: {syn.get("confidence",0):.0%}</span></div>'
                            f'<div style="font-size:0.82rem;color:{TEXT_PRIMARY};line-height:1.6;">'
                            f'{syn.get("decision_note","")[:400]}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.success("Pipeline complete. Debate responses are now enriched with full analysis.")
                    except Exception as e:
                        st.error(f"Error: {e}")
