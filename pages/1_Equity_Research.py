"""Equity Research page — Institutional Research Terminal."""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd
from datetime import datetime

from schemas.thesis import EquityThesis, ThesisClaim, ThesisDirection
from persistence.thesis_store import ThesisStore
from governance.drift_detection import DriftDetector
from ui.styles import (
    inject, ACCENT, POSITIVE, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, BG_CARD, BG_PANEL, BORDER,
    FONT_MONO, PLOTLY_LAYOUT,
)
from ui.components import (
    render_kpi_row, kpi_card, confidence_bar, confidence_badge_html,
    alert_card, divider, render_workflow_steps, panel_header, badge,
)
from ui.header import render_header

st.set_page_config(page_title="Equity Research | IIS", layout="wide")
inject()
render_header()

# ── Ticker input ──────────────────────────────────────────────────────

col_input, col_ticker_display = st.columns([1, 3])
with col_input:
    ticker = st.text_input("Ticker Symbol", value="AAPL", max_chars=10,
                           help="Enter any US equity ticker").upper().strip()
with col_ticker_display:
    st.markdown(
        f'<div style="padding-top:24px;">'
        f'<span style="font-size:1.6rem;font-weight:700;color:{TEXT_PRIMARY};'
        f'font-family:{FONT_MONO};letter-spacing:-0.02em;">{ticker}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

divider()

tab_thesis, tab_news, tab_earnings, tab_scenario, tab_drift = st.tabs([
    "Thesis", "News & Narrative", "Earnings Intelligence",
    "Scenario Tests", "Drift Detection",
])

# ── Thesis tab ────────────────────────────────────────────────────────
with tab_thesis:
    panel_header(f"Investment Thesis \u2014 {ticker}")

    if st.button("Generate AI Thesis", key="gen_thesis", type="primary",
                 help="Runs the Equity Analyst Agent across all data sources"):
        steps = [
            ("Market Data", "active"), ("SEC Filings", "pending"),
            ("Earnings", "pending"), ("News Flow", "pending"),
            ("Synthesis", "pending"),
        ]
        step_container = st.empty()
        with step_container:
            render_workflow_steps(steps, 0)

        with st.spinner("Equity Analyst Agent analyzing..."):
            try:
                from agents.equity_analyst import EquityAnalystAgent
                from mcp_servers.alpha_vantage import AlphaVantageMCP
                from mcp_servers.fmp import FMPMCP
                from mcp_servers.sec_edgar import SecEdgarMCP
                from mcp_servers.gdelt import GdeltMCP

                agent = EquityAnalystAgent()
                agent.register_tool("mcp_marketdata_alpha_vantage", AlphaVantageMCP())
                agent.register_tool("mcp_events_fmp", FMPMCP())
                agent.register_tool("mcp_filings_sec_edgar", SecEdgarMCP())
                agent.register_tool("mcp_news_gdelt", GdeltMCP())

                result = agent.run({"ticker": ticker})
                st.session_state[f"thesis_{ticker}"] = result

                store = ThesisStore()
                thesis = EquityThesis.model_validate(result)
                store.save(thesis)

                with step_container:
                    render_workflow_steps([
                        ("Market Data", "done"), ("SEC Filings", "done"),
                        ("Earnings", "done"), ("News Flow", "done"),
                        ("Synthesis", "done"),
                    ], 4)
                st.success("Thesis generated and saved.")
            except Exception as e:
                st.error(f"Error: {e}")

    thesis_data = st.session_state.get(f"thesis_{ticker}")
    if thesis_data:
        conf = thesis_data.get("confidence", 0)
        direction = thesis_data.get("direction", "neutral")
        dir_color = {
            "bull": POSITIVE, "bear": DANGER, "neutral": TEXT_DIM,
        }.get(direction, TEXT_DIM)
        dir_variant = {"bull": "pos", "bear": "neg"}.get(direction, "neutral")
        val_signal = thesis_data.get("valuation_signal", "\u2014").upper()

        # ── Header strip: direction / valuation / confidence ──
        st.markdown(
            f'<div style="display:flex;gap:16px;align-items:center;'
            f'padding:12px 16px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-radius:4px;margin-bottom:16px;">'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};">Direction</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{dir_color};'
            f'font-family:{FONT_MONO};">{direction.upper()}</div></div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};">Valuation Signal</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY};'
            f'font-family:{FONT_MONO};">{val_signal}</div></div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};">Confidence</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY};'
            f'font-family:{FONT_MONO};">{conf:.0%}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Summary (front and center, not hidden) ──
        summary = thesis_data.get("summary", "")
        if summary:
            st.markdown(
                f'<div style="padding:16px 20px;background:{BG_CARD};border:1px solid {BORDER};'
                f'border-left:3px solid {ACCENT};border-radius:4px;margin-bottom:16px;'
                f'line-height:1.65;font-size:0.88rem;color:{TEXT_MUTED};">'
                f'{summary}</div>',
                unsafe_allow_html=True,
            )

        # ── Bull vs Bear side by side ──
        col_bull, col_bear = st.columns(2)
        with col_bull:
            bull = thesis_data.get("bull_case", "")
            if bull:
                st.markdown(
                    f'<div class="t-thesis t-thesis-bull">'
                    f'<div style="font-weight:600;color:{POSITIVE};margin-bottom:10px;'
                    f'font-size:0.78rem;letter-spacing:0.05em;">BULL CASE</div>'
                    f'<div style="font-size:0.85rem;color:{TEXT_MUTED};line-height:1.6;">'
                    f'{bull}</div></div>',
                    unsafe_allow_html=True,
                )
        with col_bear:
            bear = thesis_data.get("bear_case", "")
            if bear:
                st.markdown(
                    f'<div class="t-thesis t-thesis-bear">'
                    f'<div style="font-weight:600;color:{DANGER};margin-bottom:10px;'
                    f'font-size:0.78rem;letter-spacing:0.05em;">BEAR CASE</div>'
                    f'<div style="font-size:0.85rem;color:{TEXT_MUTED};line-height:1.6;">'
                    f'{bear}</div></div>',
                    unsafe_allow_html=True,
                )

        divider()

        # ── Catalysts & Risks in styled lists ──
        catalysts = thesis_data.get("catalysts", [])
        risks = thesis_data.get("risks", [])
        if catalysts or risks:
            col_cat, col_risk = st.columns(2)
            with col_cat:
                if catalysts:
                    st.markdown(
                        f'<div style="font-size:0.78rem;font-weight:600;color:{POSITIVE};'
                        f'letter-spacing:0.05em;margin-bottom:8px;">CATALYSTS</div>',
                        unsafe_allow_html=True,
                    )
                    for c in catalysts:
                        st.markdown(
                            f'<div style="padding:4px 0 4px 12px;border-left:2px solid {POSITIVE};'
                            f'margin:3px 0;font-size:0.82rem;color:{TEXT_MUTED};">{c}</div>',
                            unsafe_allow_html=True,
                        )
            with col_risk:
                if risks:
                    st.markdown(
                        f'<div style="font-size:0.78rem;font-weight:600;color:{DANGER};'
                        f'letter-spacing:0.05em;margin-bottom:8px;">KEY RISKS</div>',
                        unsafe_allow_html=True,
                    )
                    for r in risks:
                        st.markdown(
                            f'<div style="padding:4px 0 4px 12px;border-left:2px solid {DANGER};'
                            f'margin:3px 0;font-size:0.82rem;color:{TEXT_MUTED};">{r}</div>',
                            unsafe_allow_html=True,
                        )
            divider()

        # ── Scenarios (estimated % impact under stress conditions) ──
        scenarios = thesis_data.get("scenarios", [])
        if scenarios:
            panel_header("Scenario Analysis", "estimated stock impact")
            sc_cols = st.columns(len(scenarios[:4]))
            for col, sc in zip(sc_cols, scenarios[:4]):
                with col:
                    if isinstance(sc, dict):
                        name = sc.get("name", sc.get("scenario", "Scenario"))
                        impact = sc.get("impact", 0)
                        prob = sc.get("probability", None)
                        desc = sc.get("description", "")
                        try:
                            impact_num = float(impact)
                            impact_str = f"{impact_num:+.0f}%"
                            impact_color = POSITIVE if impact_num > 0 else DANGER if impact_num < 0 else TEXT_DIM
                        except (ValueError, TypeError):
                            impact_str = str(impact)
                            impact_color = TEXT_MUTED
                        prob_html = (
                            f'<div style="font-size:0.65rem;color:{TEXT_DIM};margin-top:4px;">'
                            f'{prob:.0%} probability</div>'
                        ) if prob is not None else ""
                        desc_html = (
                            f'<div style="font-size:0.72rem;color:{TEXT_DIM};margin-top:6px;">'
                            f'{desc}</div>'
                        ) if desc else ""
                        st.markdown(
                            f'<div style="padding:12px;background:{BG_CARD};border:1px solid {BORDER};'
                            f'border-radius:4px;text-align:center;">'
                            f'<div style="font-size:0.7rem;color:{TEXT_DIM};text-transform:uppercase;'
                            f'letter-spacing:0.05em;">{name}</div>'
                            f'<div style="font-size:1.4rem;font-weight:700;color:{impact_color};'
                            f'font-family:{FONT_MONO};margin-top:4px;">{impact_str}</div>'
                            f'{prob_html}{desc_html}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"- {sc}")
            divider()

        # ── Claims (thesis claims for drift tracking) ──
        claims = thesis_data.get("claims", [])
        if claims:
            with st.expander(f"Thesis Claims ({len(claims)})"):
                for cl in claims:
                    if isinstance(cl, dict):
                        text = cl.get("text", str(cl))
                        cl_dir = cl.get("direction", "neutral")
                        cl_conf = cl.get("confidence", 0)
                        cl_color = {
                            "bull": POSITIVE, "bear": DANGER,
                        }.get(cl_dir, TEXT_DIM)
                        st.markdown(
                            f'<div style="padding:6px 10px;border-left:2px solid {cl_color};'
                            f'margin:4px 0;background:{BG_CARD};border-radius:0 3px 3px 0;">'
                            f'<div style="font-size:0.82rem;color:{TEXT_MUTED};">{text}</div>'
                            f'<div style="font-size:0.68rem;color:{TEXT_DIM};margin-top:3px;">'
                            f'{cl_dir.upper()} \u00b7 {cl_conf:.0%} confidence</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"- {cl}")

        # ── Raw data at the very bottom ──
        with st.expander("Raw Data"):
            st.json(thesis_data)
    else:
        store = ThesisStore()
        existing = store.get_by_ticker(ticker)
        if existing:
            latest = existing[0]
            st.markdown(
                alert_card("info", "Saved Thesis Found",
                           f"Thesis for {ticker} from {latest.created_at}",
                           "Click below to load it"),
                unsafe_allow_html=True,
            )
            if st.button("Load Saved Thesis"):
                st.session_state[f"thesis_{ticker}"] = latest.model_dump(mode="json")
                st.rerun()
        else:
            st.markdown(
                alert_card("info", "No Thesis",
                           f"Generate an AI thesis for {ticker} to get started.",
                           "Pulls data from Alpha Vantage, FMP, SEC EDGAR, GDELT"),
                unsafe_allow_html=True,
            )

# ── News tab ──────────────────────────────────────────────────────────
with tab_news:
    panel_header(f"News & Narrative \u2014 {ticker}")

    col_fetch_n, col_ai_n = st.columns(2)
    with col_fetch_n:
        fetch_news = st.button("Fetch Latest News", key="fetch_news", type="primary")
    with col_ai_n:
        score_news = st.button("AI Sentiment Scoring", key="score_news",
                               help="Uses LLM to score sentiment on fetched articles")

    if fetch_news:
        with st.spinner(f"Fetching news for {ticker}..."):
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker.replace(".", "-"))
                raw_news = stock.news or []
                articles = []
                for item in raw_news[:25]:
                    content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
                    pub = content.get("provider", {})
                    thumb = content.get("thumbnail")
                    thumb_url = ""
                    if isinstance(thumb, dict):
                        resolutions = thumb.get("resolutions", [])
                        if resolutions:
                            thumb_url = resolutions[-1].get("url", "")

                    articles.append({
                        "title": content.get("title") or item.get("title", "Untitled"),
                        "url": content.get("canonicalUrl", {}).get("url", "") or item.get("link", ""),
                        "publisher": pub.get("displayName", "") if isinstance(pub, dict) else str(pub),
                        "published": content.get("pubDate", "") or item.get("published", ""),
                        "summary": content.get("summary", ""),
                        "thumbnail": thumb_url,
                    })
                st.session_state[f"news_{ticker}"] = articles
                if not articles:
                    st.info("No recent news found for this ticker.")
            except Exception as e:
                st.error(f"Error fetching news: {e}")

    if score_news:
        cached_articles = st.session_state.get(f"news_{ticker}", [])
        if not cached_articles:
            st.warning("Fetch news first, then run AI scoring.")
        else:
            with st.spinner("News Sentiment Agent scoring..."):
                try:
                    from agents.news_sentiment import NewsSentimentAgent
                    from mcp_servers.gdelt import GdeltMCP

                    agent = NewsSentimentAgent()
                    agent.register_tool("mcp_news_gdelt", GdeltMCP())
                    result = agent.run({
                        "query": ticker, "max_records": 20, "timespan": "7d",
                        "articles": cached_articles,
                    })
                    st.session_state[f"sentiment_{ticker}"] = result
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── AI sentiment results ──
    sentiment = st.session_state.get(f"sentiment_{ticker}")
    if sentiment and sentiment.get("aggregate"):
        agg = sentiment["aggregate"]
        overall = agg.get("overall_sentiment", "neutral")
        s_variant = {"bullish": "pos", "bearish": "neg"}.get(overall, "neutral")

        render_kpi_row([
            ("Overall Sentiment", overall.upper(), "", s_variant),
            ("AI Confidence", f"{agg.get('confidence', 0):.0%}", "", "neutral"),
            ("Articles Scored", str(sentiment.get("article_count", 0)), "", "neutral"),
        ])

        themes = agg.get("dominant_themes", [])
        flags = agg.get("risk_flags", [])
        if themes:
            st.markdown(f"**Dominant Themes:** " + " \u00b7 ".join(themes))
        if flags:
            st.markdown(
                alert_card("critical", "Risk Flags Detected", " \u00b7 ".join(flags),
                           "May warrant review before trading"),
                unsafe_allow_html=True,
            )
        divider()

    # ── Article list ──
    articles_list = st.session_state.get(f"news_{ticker}", [])
    if articles_list:
        st.markdown(
            f'<span style="color:{TEXT_DIM};font-size:0.8rem;">'
            f'{len(articles_list)} articles from Yahoo Finance</span>',
            unsafe_allow_html=True,
        )
        for idx, art in enumerate(articles_list):
            title = art.get("title", "Untitled")
            publisher = art.get("publisher", "")
            pub_date = art.get("published", "")
            url = art.get("url", "")
            summary = art.get("summary", "")

            if pub_date:
                try:
                    from datetime import datetime as _dt
                    if "T" in str(pub_date):
                        dt = _dt.fromisoformat(str(pub_date).replace("Z", "+00:00"))
                        pub_date = dt.strftime("%b %d, %Y %H:%M")
                except Exception:
                    pass

            with st.expander(f"{title[:90]}"):
                col_info, col_link = st.columns([4, 1])
                with col_info:
                    meta_parts = []
                    if publisher:
                        meta_parts.append(publisher)
                    if pub_date:
                        meta_parts.append(str(pub_date))
                    st.caption(" \u00b7 ".join(meta_parts) if meta_parts else "\u2014")
                    if summary:
                        st.markdown(
                            f'<div style="font-size:0.82rem;color:{TEXT_MUTED};'
                            f'line-height:1.5;margin-top:4px;">{summary}</div>',
                            unsafe_allow_html=True,
                        )
                with col_link:
                    if url:
                        st.markdown(
                            f'<a href="{url}" target="_blank" style="'
                            f'display:inline-block;padding:6px 12px;background:{ACCENT};'
                            f'color:#fff;border-radius:4px;font-size:0.75rem;'
                            f'text-decoration:none;text-align:center;margin-top:4px;">'
                            f'Read \u2192</a>',
                            unsafe_allow_html=True,
                        )

# ── Earnings Intelligence tab ────────────────────────────────────────
with tab_earnings:
    panel_header(f"Earnings Intelligence \u2014 {ticker}")

    if st.button("Fetch Earnings Data", key="fetch_earnings", type="primary"):
        with st.spinner(f"Fetching earnings data for {ticker}..."):
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker.replace(".", "-"))
                earn_data: dict = {}

                info = stock.info or {}
                earn_data["info"] = {
                    "price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
                    "market_cap": info.get("marketCap", 0),
                    "pe_trailing": info.get("trailingPE"),
                    "pe_forward": info.get("forwardPE"),
                    "eps_trailing": info.get("trailingEps"),
                    "eps_forward": info.get("forwardEps"),
                    "revenue": info.get("totalRevenue", 0),
                    "revenue_growth": info.get("revenueGrowth"),
                    "profit_margin": info.get("profitMargins"),
                    "sector": info.get("sector", "\u2014"),
                    "industry": info.get("industry", "\u2014"),
                    "dividend_yield": info.get("dividendYield"),
                    "beta": info.get("beta"),
                    "52w_high": info.get("fiftyTwoWeekHigh"),
                    "52w_low": info.get("fiftyTwoWeekLow"),
                    "avg_volume": info.get("averageVolume"),
                    "short_name": info.get("shortName", ticker),
                }

                try:
                    eq = stock.earnings
                    if eq is not None and not eq.empty:
                        earn_data["annual_earnings"] = eq.reset_index().to_dict("records")
                except Exception:
                    pass

                try:
                    qe = stock.quarterly_earnings
                    if qe is not None and not qe.empty:
                        earn_data["quarterly_earnings"] = qe.reset_index().to_dict("records")
                except Exception:
                    pass

                try:
                    qf = stock.quarterly_financials
                    if qf is not None and not qf.empty:
                        earn_data["quarterly_financials"] = qf.T.head(8).reset_index().to_dict("records")
                except Exception:
                    pass

                try:
                    cal = stock.calendar
                    if cal is not None:
                        if isinstance(cal, pd.DataFrame) and not cal.empty:
                            earn_data["calendar"] = cal.to_dict()
                        elif isinstance(cal, dict):
                            earn_data["calendar"] = cal
                except Exception:
                    pass

                st.session_state[f"yf_earnings_{ticker}"] = earn_data
            except Exception as e:
                st.error(f"Error: {e}")

    earn = st.session_state.get(f"yf_earnings_{ticker}")
    if earn:
        info = earn.get("info", {})

        # ── Company overview KPIs ──
        price = info.get("price", 0)
        mcap = info.get("market_cap", 0)
        mcap_str = f"${mcap/1e12:,.2f}T" if mcap >= 1e12 else f"${mcap/1e9:,.1f}B" if mcap >= 1e9 else f"${mcap/1e6:,.0f}M"

        render_kpi_row([
            ("Price", f"${price:,.2f}" if price else "\u2014", "", "neutral"),
            ("Market Cap", mcap_str if mcap else "\u2014", "", "neutral"),
            ("Trailing P/E", f"{info['pe_trailing']:.1f}" if info.get("pe_trailing") else "\u2014", "", "neutral"),
            ("Forward P/E", f"{info['pe_forward']:.1f}" if info.get("pe_forward") else "\u2014", "", "neutral"),
        ])

        divider()

        col_eps, col_rev = st.columns(2)
        with col_eps:
            eps_t = info.get("eps_trailing")
            eps_f = info.get("eps_forward")
            render_kpi_row([
                ("Trailing EPS", f"${eps_t:.2f}" if eps_t else "\u2014", "", "neutral"),
                ("Forward EPS", f"${eps_f:.2f}" if eps_f else "\u2014", "", "neutral"),
            ])
        with col_rev:
            rev = info.get("revenue", 0)
            rev_str = f"${rev/1e9:,.1f}B" if rev >= 1e9 else f"${rev/1e6:,.0f}M" if rev else "\u2014"
            rev_g = info.get("revenue_growth")
            margin = info.get("profit_margin")
            render_kpi_row([
                ("Revenue", rev_str,
                 f"{rev_g:.1%} growth" if rev_g is not None else "", "pos" if rev_g and rev_g > 0 else "neutral"),
                ("Profit Margin", f"{margin:.1%}" if margin is not None else "\u2014", "", "neutral"),
            ])

        divider()

        # ── Additional metrics strip ──
        beta = info.get("beta")
        h52 = info.get("52w_high")
        l52 = info.get("52w_low")
        div_y = info.get("dividend_yield")
        render_kpi_row([
            ("Beta", f"{beta:.2f}" if beta else "\u2014", "", "neutral"),
            ("52W High", f"${h52:,.2f}" if h52 else "\u2014",
             f"{((price/h52)-1)*100:+.1f}% from high" if h52 and price else "", "neg" if h52 and price and price < h52 else "neutral"),
            ("52W Low", f"${l52:,.2f}" if l52 else "\u2014",
             f"{((price/l52)-1)*100:+.1f}% from low" if l52 and price else "", "pos" if l52 and price and price > l52 else "neutral"),
            ("Div Yield", f"{div_y:.2%}" if div_y else "\u2014", "", "neutral"),
        ])

        divider()

        # ── Quarterly Earnings (actual vs estimate) ──
        qe = earn.get("quarterly_earnings")
        if qe:
            panel_header("Quarterly Earnings", "EPS actual vs estimate")
            qe_df = pd.DataFrame(qe)
            display_cols = [c for c in qe_df.columns if c.lower() not in ("index",)]
            if not qe_df.empty:
                st.dataframe(qe_df[display_cols] if display_cols else qe_df,
                             use_container_width=True, hide_index=True)

                if "Earnings" in qe_df.columns or "Revenue" in qe_df.columns:
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    idx = list(range(len(qe_df)))
                    labels = [str(r) for r in qe_df.iloc[:, 0]] if len(qe_df.columns) > 0 else idx

                    for col_name in qe_df.columns:
                        if col_name in ("Earnings", "Revenue", "Surprise(%)"):
                            fig.add_trace(go.Bar(x=labels, y=qe_df[col_name], name=col_name))
                    fig.update_layout(
                        height=250, barmode="group",
                        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
                        xaxis=dict(gridcolor=BORDER),
                        yaxis=dict(gridcolor=BORDER),
                    )
                    st.plotly_chart(fig, use_container_width=True)

            divider()

        # ── Annual Earnings ──
        ae = earn.get("annual_earnings")
        if ae:
            panel_header("Annual Earnings")
            st.dataframe(pd.DataFrame(ae), use_container_width=True, hide_index=True)
            divider()

        # ── Quarterly Financials (revenue, net income, etc.) ──
        qf = earn.get("quarterly_financials")
        if qf:
            with st.expander("Quarterly Financials (detailed)"):
                st.dataframe(pd.DataFrame(qf), use_container_width=True, hide_index=True)

        # ── Upcoming earnings date ──
        cal = earn.get("calendar")
        if cal:
            panel_header("Upcoming Events")
            if isinstance(cal, dict):
                for k, v in cal.items():
                    if isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            st.markdown(
                                f'<div style="padding:3px 0;font-size:0.82rem;">'
                                f'<span style="color:{TEXT_DIM};">{k}:</span> '
                                f'<span style="color:{TEXT_PRIMARY};font-family:{FONT_MONO};">{sub_v}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(
                            f'<div style="padding:3px 0;font-size:0.82rem;">'
                            f'<span style="color:{TEXT_DIM};">{k}:</span> '
                            f'<span style="color:{TEXT_PRIMARY};font-family:{FONT_MONO};">{v}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

# ── Scenario Tests tab ───────────────────────────────────────────────
with tab_scenario:
    panel_header(f"Scenario Analysis \u2014 {ticker}")

    st.markdown(
        f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin-bottom:16px;'
        f'padding:10px 14px;background:{BG_PANEL};border:1px solid {BORDER};border-radius:6px;'
        f'line-height:1.6;">'
        f'Describe any scenario \u2014 macro shock, company event, regulatory change, '
        f'geopolitical crisis, technology shift \u2014 and the AI will analyse the impact on '
        f'<strong style="color:{TEXT_PRIMARY};">{ticker}</strong> with structured output.</div>',
        unsafe_allow_html=True,
    )

    scenario_presets = {
        "Custom": "",
        "Rate Shock (+200bp)": "Interest rates rise 200bp, triggering risk-off sentiment and recession fears",
        "Severe Recession": "Global recession: GDP contracts 3%, unemployment doubles, credit spreads widen 400bp",
        "AI Boom": "Massive AI adoption cycle: enterprise spending surges, semiconductor demand doubles",
        "Geopolitical Crisis": "Major geopolitical conflict disrupts supply chains and energy markets",
        "Stagflation": "Persistent inflation above 6% with stalling GDP growth and rising unemployment",
        "China Decoupling": "Full trade decoupling with China: tariffs escalate, supply chains forced to relocate",
        "Tech Regulation": "Sweeping antitrust action breaks up major tech platforms, new data privacy laws enacted",
        "Energy Transition": "Rapid energy transition: carbon tax at $100/ton, fossil fuel stranded assets materialise",
    }

    preset = st.selectbox("Scenario Presets", list(scenario_presets.keys()), key="scen_preset")
    default_text = scenario_presets.get(preset, "")

    scenario_desc = st.text_area(
        "Describe your scenario",
        value=default_text,
        height=100,
        placeholder="e.g. What happens to this stock if the EU imposes a 10% digital services tax? "
                    "Or: Apple loses a major patent lawsuit and must pay $20B in damages...",
    )

    def _run_scenario_analysis(tkr: str, scenario: str) -> dict:
        """Call LLM directly for fast, focused scenario analysis."""
        import json as _json
        from config import settings

        # Quick ticker context from yfinance
        context_str = ""
        try:
            import yfinance as yf
            info = yf.Ticker(tkr).info
            context_str = (
                f"Company: {info.get('longName', tkr)} | Sector: {info.get('sector', 'N/A')} | "
                f"Industry: {info.get('industry', 'N/A')} | "
                f"Market Cap: ${info.get('marketCap', 0)/1e9:.1f}B | "
                f"P/E: {info.get('trailingPE', 'N/A')} | "
                f"Revenue: ${info.get('totalRevenue', 0)/1e9:.1f}B | "
                f"Profit Margin: {info.get('profitMargins', 0):.1%} | "
                f"Beta: {info.get('beta', 'N/A')} | "
                f"52wk Range: ${info.get('fiftyTwoWeekLow', 0):.0f}-${info.get('fiftyTwoWeekHigh', 0):.0f} | "
                f"Price: ${info.get('currentPrice', info.get('previousClose', 0)):.2f}"
            )
        except Exception:
            context_str = f"Ticker: {tkr}"

        system = (
            "You are a senior scenario analyst at an institutional investment firm. "
            "Given a company and a hypothetical scenario, produce a detailed impact analysis. "
            "Be specific with numbers, percentages, and timeframes. "
            "Return ONLY valid JSON (no markdown fences)."
        )

        prompt = f"""Analyse the impact of the following scenario on {tkr}.

COMPANY CONTEXT:
{context_str}

SCENARIO:
{scenario}

Return valid JSON:
{{
  "scenario_title": "short title for this scenario",
  "overall_impact": "positive|negative|mixed",
  "confidence": 0.0-1.0,
  "summary": "2-3 sentence executive summary of the impact",
  "stock_impact_pct": estimated percentage impact on stock price (number),
  "probability": estimated probability of this scenario (0.0-1.0),
  "timeframe": "near-term|medium-term|long-term",
  "transmission_channels": [
    {{"channel": "name of transmission channel", "description": "how this channel affects the company", "magnitude": "high|medium|low"}}
  ],
  "upside_factors": ["factor that could make impact better than expected"],
  "downside_risks": ["factor that could make impact worse than expected"],
  "mitigation_actions": ["what the company could do to mitigate"],
  "second_order_effects": ["indirect consequences that follow from the primary impact"],
  "comparable_precedents": ["historical precedent or analogy"],
  "key_metrics_to_watch": ["metric or data point to monitor"]
}}"""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

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
                    kwargs["max_completion_tokens"] = 4096
                else:
                    kwargs["temperature"] = 0.3
                    kwargs["max_tokens"] = 4096
                resp = client.chat.completions.create(**kwargs)
            else:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=settings.LLM_MODEL, messages=messages,
                    temperature=0.3, max_tokens=4096,
                )
            raw = resp.choices[0].message.content or ""
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1]
                if clean.endswith("```"):
                    clean = clean[:-3]
            return _json.loads(clean.strip())
        except Exception as e:
            return {"error": str(e), "scenario_title": scenario[:60], "summary": f"Analysis failed: {e}"}

    if st.button("Run Scenario Analysis", key="run_scenario", type="primary"):
        if not scenario_desc.strip():
            st.warning("Please describe a scenario or select a preset.")
        else:
            with st.spinner("Analysing scenario impact..."):
                result = _run_scenario_analysis(ticker, scenario_desc)
                st.session_state[f"scenario_{ticker}"] = result
                if "scenario_chat" in st.session_state:
                    del st.session_state["scenario_chat"]

    scenario_data = st.session_state.get(f"scenario_{ticker}")
    if scenario_data and "error" not in scenario_data:
        title = scenario_data.get("scenario_title", "Scenario")
        impact = scenario_data.get("overall_impact", "mixed")
        conf = scenario_data.get("confidence", 0)
        stock_pct = scenario_data.get("stock_impact_pct", 0)
        prob = scenario_data.get("probability", 0)
        timeframe = scenario_data.get("timeframe", "medium-term")

        impact_color = POSITIVE if impact == "positive" else DANGER if impact == "negative" else WARNING

        try:
            stock_pct_num = float(stock_pct)
        except (ValueError, TypeError):
            stock_pct_num = 0
        pct_color = POSITIVE if stock_pct_num > 0 else DANGER if stock_pct_num < 0 else TEXT_DIM

        try:
            prob_num = float(prob)
            prob_str = f"{prob_num:.0%}" if prob_num <= 1 else f"{prob_num:.0f}%"
        except (ValueError, TypeError):
            prob_str = str(prob) if prob else "\u2014"

        # ── Impact header ──
        st.markdown(
            f'<div style="padding:16px 20px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-left:4px solid {impact_color};border-radius:4px;margin:12px 0;">'
            f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};margin-bottom:6px;">Scenario</div>'
            f'<div style="font-size:1rem;font-weight:700;color:{TEXT_PRIMARY};margin-bottom:12px;">'
            f'{title}</div>'
            f'<div style="display:flex;gap:24px;flex-wrap:wrap;">'
            f'<div><span style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};display:block;">Impact</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:{impact_color};'
            f'font-family:{FONT_MONO};">{impact.upper()}</span></div>'
            f'<div><span style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};display:block;">Stock Price Effect</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:{pct_color};'
            f'font-family:{FONT_MONO};">{stock_pct_num:+.0f}%</span></div>'
            f'<div><span style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};display:block;">Probability</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY};'
            f'font-family:{FONT_MONO};">{prob_str}</span></div>'
            f'<div><span style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};display:block;">Timeframe</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY};'
            f'font-family:{FONT_MONO};">{timeframe.upper()}</span></div>'
            f'<div><span style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};display:block;">Confidence</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY};'
            f'font-family:{FONT_MONO};">{conf:.0%}</span></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        confidence_bar(conf, "Analysis Confidence")

        # ── Summary ──
        s_summary = scenario_data.get("summary", "")
        if s_summary:
            st.markdown(
                f'<div style="padding:16px 20px;background:{BG_CARD};border:1px solid {BORDER};'
                f'border-left:3px solid {ACCENT};border-radius:4px;margin:12px 0;'
                f'line-height:1.65;font-size:0.88rem;color:{TEXT_MUTED};">'
                f'{s_summary}</div>',
                unsafe_allow_html=True,
            )

        divider()

        # ── Transmission Channels ──
        channels = scenario_data.get("transmission_channels", [])
        if channels:
            st.markdown(
                f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;'
                f'color:{TEXT_DIM};font-weight:600;margin-bottom:10px;">Transmission Channels</div>',
                unsafe_allow_html=True,
            )
            for ch in channels:
                ch_name = ch.get("channel", "") if isinstance(ch, dict) else str(ch)
                ch_desc = ch.get("description", "") if isinstance(ch, dict) else ""
                ch_mag = ch.get("magnitude", "medium") if isinstance(ch, dict) else "medium"
                mag_color = DANGER if ch_mag == "high" else WARNING if ch_mag == "medium" else TEXT_DIM
                st.markdown(
                    f'<div style="padding:10px 14px;background:{BG_CARD};border:1px solid {BORDER};'
                    f'border-radius:4px;margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<span style="font-weight:600;font-size:0.84rem;color:{TEXT_PRIMARY};">{ch_name}</span>'
                    f'<span style="font-size:0.65rem;font-weight:700;color:{mag_color};'
                    f'text-transform:uppercase;padding:2px 8px;border-radius:3px;'
                    f'background:rgba({",".join(str(int(mag_color.lstrip("#")[i:i+2], 16)) for i in (0,2,4))},0.12);'
                    f'">{ch_mag}</span></div>'
                    + (f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin-top:4px;'
                       f'line-height:1.5;">{ch_desc}</div>' if ch_desc else "")
                    + f'</div>',
                    unsafe_allow_html=True,
                )
            divider()

        # ── Upside / Downside side by side ──
        upside = scenario_data.get("upside_factors", [])
        downside = scenario_data.get("downside_risks", [])
        if upside or downside:
            col_up, col_down = st.columns(2)
            with col_up:
                st.markdown(
                    f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;'
                    f'color:{POSITIVE};font-weight:600;margin-bottom:6px;">Upside Factors</div>',
                    unsafe_allow_html=True,
                )
                for u in upside:
                    st.markdown(
                        f'<div style="padding:6px 0 6px 12px;border-left:2px solid {POSITIVE};'
                        f'margin:3px 0;font-size:0.82rem;color:{TEXT_MUTED};">{u}</div>',
                        unsafe_allow_html=True,
                    )
            with col_down:
                st.markdown(
                    f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;'
                    f'color:{DANGER};font-weight:600;margin-bottom:6px;">Downside Risks</div>',
                    unsafe_allow_html=True,
                )
                for d in downside:
                    st.markdown(
                        f'<div style="padding:6px 0 6px 12px;border-left:2px solid {DANGER};'
                        f'margin:3px 0;font-size:0.82rem;color:{TEXT_MUTED};">{d}</div>',
                        unsafe_allow_html=True,
                    )
            divider()

        # ── Mitigation / Second-order / Precedents / Metrics ──
        mitigation = scenario_data.get("mitigation_actions", [])
        second_order = scenario_data.get("second_order_effects", [])
        precedents = scenario_data.get("comparable_precedents", [])
        metrics = scenario_data.get("key_metrics_to_watch", [])

        info_sections = [
            ("Mitigation Actions", mitigation, WARNING),
            ("Second-Order Effects", second_order, ACCENT),
            ("Historical Precedents", precedents, "#a78bfa"),
            ("Key Metrics to Watch", metrics, "#38bdf8"),
        ]

        active_sections = [(t, items, c) for t, items, c in info_sections if items]
        if active_sections:
            cols = st.columns(min(len(active_sections), 2))
            for idx, (sec_title, sec_items, sec_color) in enumerate(active_sections):
                with cols[idx % len(cols)]:
                    st.markdown(
                        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;'
                        f'color:{sec_color};font-weight:600;margin-bottom:6px;">{sec_title}</div>',
                        unsafe_allow_html=True,
                    )
                    for item in sec_items:
                        st.markdown(
                            f'<div style="padding:5px 0 5px 12px;border-left:2px solid {sec_color};'
                            f'margin:3px 0;font-size:0.8rem;color:{TEXT_MUTED};">{item}</div>',
                            unsafe_allow_html=True,
                        )
            divider()

        # ── Follow-up chat: dig deeper into the scenario ──
        st.markdown(
            f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin:8px 0 12px;'
            f'padding:8px 14px;background:{BG_PANEL};border:1px solid {BORDER};border-radius:6px;">'
            f'Ask follow-up questions to explore this scenario further.</div>',
            unsafe_allow_html=True,
        )

        if "scenario_chat" not in st.session_state:
            st.session_state.scenario_chat = []

        for msg in st.session_state.scenario_chat:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(
                        f'<span style="font-size:0.68rem;font-weight:700;color:{ACCENT};'
                        f'letter-spacing:0.04em;text-transform:uppercase;'
                        f'font-family:{FONT_MONO};">Scenario Analyst</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(msg["content"])

        followup = st.chat_input(
            f"Ask more about this scenario for {ticker}...",
            key="scenario_followup_input",
        )

        if followup:
            st.session_state.scenario_chat.append({"role": "user", "content": followup})

            import json as _json_chat
            from config import settings as _settings

            _sys = (
                f"You are a scenario analyst. You previously analysed a scenario for {ticker}. "
                f"Here is your analysis:\n{_json_chat.dumps(scenario_data, default=str)[:2500]}\n\n"
                f"Answer the user's follow-up questions. Be specific and data-driven. "
                f"Keep answers concise (3-6 sentences) unless more detail is requested."
            )
            _msgs: list[dict] = [{"role": "system", "content": _sys}]
            for m in st.session_state.scenario_chat[-10:]:
                _msgs.append({"role": m["role"], "content": m["content"]})
            _msgs.append({"role": "user", "content": followup})

            with st.spinner("Thinking..."):
                try:
                    if _settings.use_azure:
                        from openai import AzureOpenAI as _AZ
                        _cl = _AZ(
                            azure_endpoint=_settings.AZURE_OPENAI_ENDPOINT,
                            api_key=_settings.AZURE_OPENAI_API_KEY,
                            api_version=_settings.AZURE_OPENAI_API_VERSION,
                        )
                        _kw: dict = {"model": _settings.AZURE_OPENAI_DEPLOYMENT, "messages": _msgs}
                        if _settings.AZURE_OPENAI_DEPLOYMENT.startswith("o"):
                            _kw["max_completion_tokens"] = 2048
                        else:
                            _kw["temperature"] = 0.3
                            _kw["max_tokens"] = 2048
                        _resp = _cl.chat.completions.create(**_kw)
                    else:
                        from openai import OpenAI as _OAI
                        _cl = _OAI(api_key=_settings.OPENAI_API_KEY)
                        _resp = _cl.chat.completions.create(
                            model=_settings.LLM_MODEL, messages=_msgs,
                            temperature=0.3, max_tokens=2048,
                        )
                    _answer = _resp.choices[0].message.content or "No response."
                except Exception as _e:
                    _answer = f"Error: {_e}"

            st.session_state.scenario_chat.append({"role": "assistant", "content": _answer})
            st.rerun()

        with st.expander("Raw Analysis Data"):
            st.json(scenario_data)

    elif scenario_data and "error" in scenario_data:
        st.error(f"Analysis failed: {scenario_data.get('error', 'Unknown error')}")
    else:
        st.markdown(
            alert_card("info", "No Scenario Analysed",
                       f"Describe a scenario above and run the analysis for {ticker}.",
                       "Try a preset or write your own custom scenario."),
            unsafe_allow_html=True,
        )

# ── Drift Detection tab ──────────────────────────────────────────────
with tab_drift:
    panel_header(f"Thesis Drift Detection \u2014 {ticker}")

    store = ThesisStore()
    theses = store.get_by_ticker(ticker)

    if not theses:
        st.markdown(
            alert_card("info", "No Thesis Found",
                       "Generate a thesis first in the Thesis tab.",
                       "Drift detection compares claims against new data."),
            unsafe_allow_html=True,
        )
    else:
        latest_thesis = theses[0]
        dir_color = {
            "bull": POSITIVE, "bear": DANGER, "neutral": TEXT_DIM,
        }.get(latest_thesis.direction.value if hasattr(latest_thesis.direction, 'value') else str(latest_thesis.direction), TEXT_DIM)
        dir_label = (latest_thesis.direction.value if hasattr(latest_thesis.direction, 'value') else str(latest_thesis.direction)).upper()
        st.markdown(
            f'<div style="padding:14px 18px;background:{BG_CARD};border:1px solid {BORDER};'
            f'border-left:3px solid {dir_color};border-radius:4px;margin-bottom:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<span style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{TEXT_DIM};font-weight:600;">Active Thesis</span>'
            f'<div style="display:flex;gap:10px;align-items:center;">'
            f'<span style="font-size:0.65rem;font-weight:700;color:{dir_color};'
            f'padding:2px 8px;border-radius:3px;'
            f'background:rgba({",".join(str(int(dir_color.lstrip("#")[i:i+2], 16)) for i in (0,2,4))},0.12);'
            f'text-transform:uppercase;">{dir_label}</span>'
            f'<span style="font-size:0.72rem;color:{TEXT_DIM};font-family:{FONT_MONO};">'
            f'{len(latest_thesis.claims)} claims</span>'
            f'</div></div>'
            f'<div style="font-size:0.84rem;color:{TEXT_MUTED};line-height:1.65;">'
            f'{latest_thesis.summary}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("Run Drift Check", key="drift_check", type="primary"):
            with st.spinner("Checking claims against current data..."):
                try:
                    detector = DriftDetector()
                    news = []
                    try:
                        from mcp_servers.gdelt import GdeltMCP
                        gdelt = GdeltMCP()
                        news_result = gdelt.search_news(query=ticker, max_records=10)
                        if news_result.success:
                            news = news_result.data.get("articles", [])
                    except Exception:
                        pass

                    results = detector.check_thesis(latest_thesis, current_news=news)
                    st.session_state[f"drift_{ticker}"] = [
                        r.model_dump(mode="json") for r in results
                    ]
                except Exception as e:
                    st.error(f"Error: {e}")

        drift_results = st.session_state.get(f"drift_{ticker}")
        if drift_results:
            for dr in drift_results:
                status = dr.get("status", "no_change")
                status_config = {
                    "no_change": ("success", "Holding", "Claim remains supported"),
                    "weakened": ("warning", "Weakened", "Evidence has weakened"),
                    "invalidated": ("critical", "Invalidated", "Claim no longer supported"),
                    "strengthened": ("success", "Strengthened", "New evidence supports this claim"),
                }
                sev, title, hint = status_config.get(status, ("info", "Unknown", ""))
                st.markdown(
                    alert_card(sev, title,
                               dr.get("original_text", "\u2014")[:150],
                               f"{hint} \u2014 {dr.get('evidence', '')[:200]}"),
                    unsafe_allow_html=True,
                )
                confidence_bar(dr.get("confidence", 0.5), "Check Confidence")
