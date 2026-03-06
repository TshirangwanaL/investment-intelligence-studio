"""Market & News page — Institutional Research Terminal."""

from __future__ import annotations

import json
import streamlit as st
import pandas as pd
from datetime import datetime

from ui.styles import (
    inject, ACCENT, POSITIVE, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, BG_CARD, BG_PANEL, BORDER,
    FONT_MONO, PLOTLY_LAYOUT,
)
from ui.components import (
    render_kpi_row, alert_card, divider, live_dot,
    render_hbar, kpi_card, confidence_bar, panel_header, badge,
)
from ui.header import render_header

st.set_page_config(page_title="Market & News | IIS", layout="wide")
inject()
render_header()

tab_regime, tab_news, tab_calendar = st.tabs([
    "Macro Regime", "News Search", "Catalyst Calendar",
])

# ── Macro Regime ──────────────────────────────────────────────────────
with tab_regime:
    panel_header("Macro Regime Detection")

    col_fetch, col_classify = st.columns(2)
    with col_fetch:
        fetch_macro = st.button("Fetch Macro Indicators", key="fetch_macro", type="primary")
    with col_classify:
        classify_regime = st.button("AI Regime Classification", key="classify_regime")

    if fetch_macro:
        with st.spinner("Querying FRED..."):
            try:
                from mcp_servers.fred import FredMCP
                fred = FredMCP()
                result = fred.get_macro_dashboard()
                st.session_state["macro_dashboard"] = result.to_dict()
            except Exception as e:
                st.error(f"Error: {e}")

    if classify_regime:
        with st.spinner("Market Narrative Agent analyzing regime..."):
            try:
                from agents.market_narrative import MarketNarrativeAgent
                from mcp_servers.fred import FredMCP
                from mcp_servers.gdelt import GdeltMCP
                from mcp_servers.alpha_vantage import AlphaVantageMCP

                agent = MarketNarrativeAgent()
                agent.register_tool("mcp_macro_fred", FredMCP())
                agent.register_tool("mcp_news_gdelt", GdeltMCP())
                agent.register_tool("mcp_marketdata_alpha_vantage", AlphaVantageMCP())
                result = agent.run({})
                st.session_state["regime_classification"] = result
            except Exception as e:
                st.error(f"Error: {e}")

    regime = st.session_state.get("regime_classification")
    if regime:
        label = regime.get("regime_label", "uncertain").upper()
        conf = regime.get("regime_confidence", 0)
        sentiment = regime.get("risk_sentiment", "neutral")

        regime_colors = {
            "RISK_ON": (POSITIVE, "pos"),
            "RISK_OFF": (DANGER, "neg"),
            "TRANSITION": (WARNING, "warn"),
            "UNCERTAIN": (TEXT_DIM, "neutral"),
        }
        rc, rv = regime_colors.get(label, (TEXT_DIM, "neutral"))

        st.markdown(
            f'<div style="background:{BG_CARD};border:1px solid {rc};border-radius:4px;'
            f'padding:20px;margin:12px 0;text-align:center;">'
            f'<div style="font-size:1.5rem;font-weight:700;color:{rc};'
            f'font-family:{FONT_MONO};letter-spacing:0.05em;">{label}</div>'
            f'<div style="font-size:0.8rem;color:{TEXT_MUTED};margin-top:4px;">'
            f'{sentiment.title()} sentiment \u00b7 {conf:.0%} confidence</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        confidence_bar(conf, "Regime Classification Confidence")
        st.markdown(f"**Summary:** {regime.get('summary', '\u2014')}")

        col_drivers, col_themes = st.columns(2)
        with col_drivers:
            panel_header("Macro Drivers")
            for d in regime.get("macro_drivers", []):
                st.markdown(f"- {d}")
        with col_themes:
            panel_header("Sector Themes")
            for t in regime.get("sector_themes", []):
                st.markdown(f"- {t}")

        divider()

    macro = st.session_state.get("macro_dashboard")
    if macro and macro.get("data"):
        data = macro["data"]
        st.markdown(
            f'<div style="margin-bottom:8px;">'
            f'<span style="font-size:0.85rem;font-weight:600;color:{TEXT_PRIMARY};">'
            f'Key Economic Indicators</span> {live_dot("Latest")}</div>',
            unsafe_allow_html=True,
        )

        indicators = [
            ("CPI", "Inflation (CPI)", "%"),
            ("FED_FUNDS", "Fed Funds Rate", "%"),
            ("UNEMPLOYMENT", "Unemployment", "%"),
            ("T10Y2Y", "10Y-2Y Spread", "bp"),
        ]

        kpis = []
        for key, lbl, unit in indicators:
            series = data.get(key, {})
            latest = series.get("latest", {})
            val = latest.get("value", "N/A") if latest else "N/A"
            date = latest.get("date", "") if latest else ""
            kpis.append((lbl, f"{val}{unit if val != 'N/A' else ''}", f"As of {date}", "neutral"))

        render_kpi_row(kpis)
        divider()

        for key, series_data in data.items():
            if "error" in series_data or key in [k for k, _, _ in indicators]:
                continue
            recent = series_data.get("recent", [])
            if recent:
                with st.expander(f"{key} \u2014 {series_data.get('series_id', '')}"):
                    st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)

# ── News Search ───────────────────────────────────────────────────────
with tab_news:
    panel_header("News Search")

    news_source = st.radio(
        "Source", ["Yahoo Finance (per ticker)", "GDELT (keyword search)"],
        horizontal=True, key="news_source",
    )

    if news_source.startswith("Yahoo"):
        col_tickers, col_go = st.columns([4, 1])
        with col_tickers:
            yf_tickers = st.text_input(
                "Tickers (comma-separated)",
                value="AAPL, MSFT, NVDA",
                key="yf_news_tickers",
            )
        with col_go:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            do_yf = st.button("Fetch News", key="yf_news_go", type="primary")

        if do_yf:
            with st.spinner("Fetching news from Yahoo Finance..."):
                try:
                    import yfinance as yf
                    all_articles = []
                    for t in [x.strip().upper() for x in yf_tickers.split(",") if x.strip()]:
                        stock = yf.Ticker(t.replace(".", "-"))
                        for item in (stock.news or [])[:10]:
                            content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
                            pub = content.get("provider", {})
                            pub_name = pub.get("displayName", "") if isinstance(pub, dict) else str(pub)
                            all_articles.append({
                                "ticker": t,
                                "title": content.get("title") or item.get("title", "Untitled"),
                                "url": content.get("canonicalUrl", {}).get("url", "") or item.get("link", ""),
                                "publisher": pub_name,
                                "published": content.get("pubDate", "") or item.get("published", ""),
                                "summary": content.get("summary", ""),
                            })
                    st.session_state["yf_global_news"] = all_articles
                except Exception as e:
                    st.error(f"Error: {e}")

        yf_articles = st.session_state.get("yf_global_news", [])
        if yf_articles:
            st.caption(f"{len(yf_articles)} articles")
            for art in yf_articles:
                title = art.get("title", "Untitled")
                tkr_badge = art.get("ticker", "")
                publisher = art.get("publisher", "")
                pub_date = art.get("published", "")
                url = art.get("url", "")
                summary = art.get("summary", "")

                if pub_date:
                    try:
                        from datetime import datetime as _dt
                        if "T" in str(pub_date):
                            dt = _dt.fromisoformat(str(pub_date).replace("Z", "+00:00"))
                            pub_date = dt.strftime("%b %d, %H:%M")
                    except Exception:
                        pass

                with st.expander(f"[{tkr_badge}]  {title[:85]}"):
                    col_info, col_link = st.columns([4, 1])
                    with col_info:
                        meta = " \u00b7 ".join(filter(None, [publisher, str(pub_date)]))
                        st.caption(meta or "\u2014")
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
                                f'text-decoration:none;text-align:center;">Read \u2192</a>',
                                unsafe_allow_html=True,
                            )

    else:
        col_q, col_t, col_n = st.columns([3, 1, 1])
        with col_q:
            query = st.text_input("Search query", value="inflation recession", key="news_q")
        with col_t:
            timespan = st.selectbox("Timespan", ["1d", "3d", "7d", "14d", "30d"], index=2)
        with col_n:
            max_records = st.number_input("Results", 10, 100, 30, step=10)

        st.markdown(
            alert_card("warning", "GDELT Rate Limits",
                       "GDELT requires \u22655 seconds between requests. "
                       "If you get no results, wait 10s and retry.",
                       "Free public API \u2014 no key needed"),
            unsafe_allow_html=True,
        )

        col_search, col_ai = st.columns(2)
        with col_search:
            do_search = st.button("Search GDELT", key="search_gdelt", type="primary")
        with col_ai:
            do_ai = st.button("AI Sentiment Analysis", key="ai_news_sentiment")

        if do_search:
            with st.spinner("Querying GDELT (may take ~6s due to rate limit)..."):
                try:
                    from mcp_servers.gdelt import GdeltMCP
                    gdelt = GdeltMCP()
                    result = gdelt.search_news(query=query, timespan=timespan,
                                               max_records=max_records)
                    st.session_state["news_search"] = result.to_dict()
                except Exception as e:
                    st.error(f"Error: {e}")

        if do_ai:
            with st.spinner("News Sentiment Agent scoring..."):
                try:
                    from agents.news_sentiment import NewsSentimentAgent
                    from mcp_servers.gdelt import GdeltMCP

                    agent = NewsSentimentAgent()
                    agent.register_tool("mcp_news_gdelt", GdeltMCP())
                    result = agent.run({
                        "query": query, "max_records": max_records, "timespan": timespan,
                    })
                    st.session_state["news_sentiment_global"] = result
                except Exception as e:
                    st.error(f"Error: {e}")

        global_sentiment = st.session_state.get("news_sentiment_global")
        s_colors = {"bullish": POSITIVE, "bearish": DANGER, "neutral": TEXT_DIM}

        if global_sentiment:
            agg = global_sentiment.get("aggregate", {})
            overall = agg.get("overall_sentiment", "neutral")

            render_kpi_row([
                ("Overall Sentiment", overall.upper(), "",
                 "pos" if overall == "bullish" else "neg" if overall == "bearish" else "neutral"),
                ("Confidence", f"{agg.get('confidence', 0):.0%}", "", "neutral"),
                ("Articles", str(global_sentiment.get("article_count", 0)), "", "neutral"),
            ])
            divider()

            for art in global_sentiment.get("articles", [])[:max_records]:
                sent = art.get("llm_sentiment", "neutral")
                sent_color = s_colors.get(sent, TEXT_DIM)
                with st.expander(f"{art.get('title', 'Untitled')[:90]}"):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.caption(
                            f"{art.get('domain', '\u2014')} \u00b7 {art.get('date', '\u2014')} "
                            f"\u00b7 {art.get('llm_category', '')}"
                        )
                        if art.get("url"):
                            st.markdown(f"[Read article \u2192]({art['url']})")
                    with c2:
                        st.markdown(
                            f'<div style="text-align:center;padding:6px;background:{BG_CARD};'
                            f'border:1px solid {BORDER};border-radius:4px;">'
                            f'<div style="font-size:0.6rem;color:{TEXT_DIM};text-transform:uppercase;">'
                            f'Sentiment</div>'
                            f'<div style="font-size:0.85rem;font-weight:700;color:{sent_color};'
                            f'font-family:{FONT_MONO};">{sent.title()}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
        else:
            news_results = st.session_state.get("news_search")
            if news_results and news_results.get("data"):
                articles = news_results["data"].get("articles", [])
                if articles:
                    st.caption(f"{len(articles)} articles")
                    for art in articles[:max_records]:
                        title = art.get("title", "Untitled")
                        tone = art.get("tone", 0)
                        tone_val = float(tone) if tone else 0
                        tone_color = POSITIVE if tone_val > 2 else DANGER if tone_val < -2 else TEXT_DIM
                        with st.expander(f"{title[:90]}"):
                            col_info, col_tone = st.columns([3, 1])
                            with col_info:
                                st.caption(
                                    f"{art.get('domain', '\u2014')} \u00b7 "
                                    f"{art.get('seendate', '\u2014')}")
                                if art.get("url"):
                                    st.markdown(f"[Read article \u2192]({art['url']})")
                            with col_tone:
                                st.markdown(
                                    f'<div style="text-align:center;padding:6px;background:{BG_CARD};'
                                    f'border:1px solid {BORDER};border-radius:4px;">'
                                    f'<div style="font-size:0.6rem;color:{TEXT_DIM};">TONE</div>'
                                    f'<div style="font-size:0.85rem;font-weight:700;color:{tone_color};'
                                    f'font-family:{FONT_MONO};">{tone_val:+.1f}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                else:
                    st.info("No articles found. GDELT may be rate-limiting — wait 10s and retry.")

# ── Catalyst Calendar ─────────────────────────────────────────────────
with tab_calendar:
    panel_header("Catalyst Calendar")

    st.markdown(
        f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin-bottom:16px;'
        f'padding:10px 14px;background:{BG_PANEL};border:1px solid {BORDER};border-radius:6px;'
        f'line-height:1.6;">'
        f'Upcoming events that can affect portfolio positioning: earnings dates, '
        f'ex-dividend dates, macro releases, and key corporate events.</div>',
        unsafe_allow_html=True,
    )

    portfolio = st.session_state.get("portfolio")
    if portfolio and hasattr(portfolio, "positions"):
        watchlist = [p.ticker for p in portfolio.positions]
    else:
        watchlist = []

    extra = st.text_input("Additional tickers", value="", key="cal_extra",
                          placeholder="NVDA, TSLA, AMZN")
    if extra:
        watchlist.extend([t.strip().upper() for t in extra.split(",") if t.strip()])

    if st.button("Fetch Catalyst Calendar", key="fetch_cal", type="primary"):
        if not watchlist:
            st.warning("Add tickers above or load a portfolio first.")
        else:
            with st.spinner("Scanning earnings, dividends, and macro events..."):
                try:
                    import yfinance as yf
                    from datetime import timedelta

                    today = datetime.now()
                    today_str = today.strftime("%Y-%m-%d")
                    events: list[dict] = []

                    for tkr in watchlist[:20]:
                        try:
                            stock = yf.Ticker(tkr.replace(".", "-"))
                            info = stock.info or {}

                            # Earnings dates
                            cal = stock.calendar
                            if cal is not None:
                                if isinstance(cal, dict):
                                    raw_dates = cal.get("Earnings Date", [])
                                    if not isinstance(raw_dates, list):
                                        raw_dates = [raw_dates]
                                    for d in raw_dates:
                                        ds = str(d)[:10]
                                        if ds >= today_str:
                                            eps_est = cal.get("EPS Average")
                                            rev_est = cal.get("Revenue Average")
                                            detail = ""
                                            if eps_est:
                                                detail += f"EPS est: ${eps_est:.2f}"
                                            if rev_est:
                                                detail += f" | Rev est: ${rev_est/1e9:.1f}B" if rev_est > 1e6 else f" | Rev est: ${rev_est:,.0f}"
                                            events.append({
                                                "date": ds, "ticker": tkr,
                                                "event": "Earnings Report",
                                                "category": "earnings",
                                                "detail": detail or "Quarterly earnings release",
                                                "impact": "high",
                                            })
                                elif hasattr(cal, "to_dict"):
                                    cal_dict = cal.to_dict() if callable(getattr(cal, "to_dict", None)) else {}
                                    for k, v in cal_dict.items():
                                        if "earning" in str(k).lower() or "date" in str(k).lower():
                                            vals = list(v.values()) if isinstance(v, dict) else [v]
                                            for val in vals:
                                                ds = str(val)[:10]
                                                if ds >= today_str:
                                                    events.append({
                                                        "date": ds, "ticker": tkr,
                                                        "event": "Earnings Report",
                                                        "category": "earnings",
                                                        "detail": str(k),
                                                        "impact": "high",
                                                    })

                            # Ex-dividend date
                            ex_div = info.get("exDividendDate")
                            if ex_div:
                                try:
                                    if isinstance(ex_div, (int, float)):
                                        from datetime import timezone
                                        ex_dt = datetime.fromtimestamp(ex_div, tz=timezone.utc)
                                    else:
                                        ex_dt = pd.to_datetime(ex_div)
                                    ds = ex_dt.strftime("%Y-%m-%d")
                                    if ds >= today_str:
                                        div_rate = info.get("dividendRate", 0)
                                        div_yield = info.get("dividendYield", 0)
                                        detail = f"${div_rate:.2f}/share" if div_rate else ""
                                        if div_yield:
                                            detail += f" ({div_yield:.1%} yield)"
                                        events.append({
                                            "date": ds, "ticker": tkr,
                                            "event": "Ex-Dividend Date",
                                            "category": "dividend",
                                            "detail": detail or "Dividend record date",
                                            "impact": "medium",
                                        })
                                except Exception:
                                    pass

                            # Key company info events
                            sector = info.get("sector", "")
                            mkt_cap = info.get("marketCap", 0)
                            beta = info.get("beta", 1.0)
                            if beta and beta > 1.5:
                                events.append({
                                    "date": today_str, "ticker": tkr,
                                    "event": "High Beta Alert",
                                    "category": "risk",
                                    "detail": f"Beta={beta:.2f} — elevated volatility risk around events",
                                    "impact": "medium",
                                })

                        except Exception:
                            continue

                    # Macro events (static calendar of known recurring events)
                    macro_events = [
                        {"name": "FOMC Rate Decision", "dates": ["2026-03-18", "2026-05-06", "2026-06-17", "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16"], "impact": "high", "detail": "Federal Reserve interest rate decision and statement"},
                        {"name": "CPI Release", "dates": ["2026-03-12", "2026-04-10", "2026-05-13", "2026-06-10", "2026-07-14", "2026-08-12"], "impact": "high", "detail": "Consumer Price Index — key inflation gauge"},
                        {"name": "Non-Farm Payrolls", "dates": ["2026-03-06", "2026-04-03", "2026-05-08", "2026-06-05", "2026-07-02", "2026-08-07"], "impact": "high", "detail": "Monthly employment report — labour market health"},
                        {"name": "GDP Report", "dates": ["2026-03-26", "2026-04-29", "2026-06-25", "2026-07-30"], "impact": "high", "detail": "Quarterly GDP growth estimate"},
                        {"name": "PCE Inflation", "dates": ["2026-03-27", "2026-04-30", "2026-05-29", "2026-06-26"], "impact": "medium", "detail": "Personal Consumption Expenditures — Fed's preferred inflation measure"},
                        {"name": "ISM Manufacturing", "dates": ["2026-03-02", "2026-04-01", "2026-05-01", "2026-06-01"], "impact": "medium", "detail": "Manufacturing purchasing managers index"},
                        {"name": "Retail Sales", "dates": ["2026-03-17", "2026-04-16", "2026-05-15", "2026-06-16"], "impact": "medium", "detail": "Monthly consumer spending indicator"},
                        {"name": "Options Expiration (OPEX)", "dates": ["2026-03-20", "2026-04-17", "2026-05-15", "2026-06-19", "2026-07-17", "2026-08-21"], "impact": "medium", "detail": "Monthly options expiry — elevated volume and volatility"},
                        {"name": "Quad Witching", "dates": ["2026-03-20", "2026-06-19", "2026-09-18", "2026-12-18"], "impact": "high", "detail": "Quarterly expiry of index options, index futures, stock options, stock futures"},
                    ]

                    for me in macro_events:
                        for d in me["dates"]:
                            if d >= today_str and d <= (today + timedelta(days=90)).strftime("%Y-%m-%d"):
                                events.append({
                                    "date": d, "ticker": "MACRO",
                                    "event": me["name"],
                                    "category": "macro",
                                    "detail": me["detail"],
                                    "impact": me["impact"],
                                })

                    events.sort(key=lambda e: e["date"])
                    st.session_state["catalyst_events"] = events
                except Exception as e:
                    st.error(f"Error: {e}")

    cal_events = st.session_state.get("catalyst_events")
    if cal_events:
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Summary KPIs
        earnings_ct = sum(1 for e in cal_events if e["category"] == "earnings")
        macro_ct = sum(1 for e in cal_events if e["category"] == "macro")
        div_ct = sum(1 for e in cal_events if e["category"] == "dividend")
        high_ct = sum(1 for e in cal_events if e["impact"] == "high")

        render_kpi_row([
            ("Total Events", str(len(cal_events)), f"Next 90 days", "neutral"),
            ("Earnings Reports", str(earnings_ct), f"{earnings_ct} companies", "neutral"),
            ("Macro Releases", str(macro_ct), "FOMC, CPI, NFP, GDP...", "neutral"),
            ("High Impact", str(high_ct), "Requires attention", "neg" if high_ct > 5 else "neutral"),
        ])

        divider()

        # Imminent events (next 7 days)
        from datetime import timedelta
        week_out = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        imminent = [e for e in cal_events if e["date"] <= week_out]

        if imminent:
            st.markdown(
                f'<div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;'
                f'color:{DANGER};font-weight:700;margin-bottom:10px;">'
                f'Next 7 Days \u2014 {len(imminent)} Events</div>',
                unsafe_allow_html=True,
            )
            for ev in imminent:
                cat = ev["category"]
                cat_color = {
                    "earnings": WARNING, "macro": ACCENT,
                    "dividend": POSITIVE, "risk": DANGER,
                }.get(cat, TEXT_DIM)
                imp = ev["impact"]
                imp_color = DANGER if imp == "high" else WARNING if imp == "medium" else TEXT_DIM

                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;'
                    f'padding:10px 14px;background:{BG_CARD};border:1px solid {BORDER};'
                    f'border-left:3px solid {cat_color};border-radius:4px;margin-bottom:6px;">'
                    f'<div style="min-width:80px;font-family:{FONT_MONO};font-size:0.78rem;'
                    f'font-weight:700;color:{TEXT_PRIMARY};">{ev["date"]}</div>'
                    f'<div style="min-width:55px;">'
                    f'<span style="font-size:0.62rem;font-weight:700;padding:2px 6px;'
                    f'border-radius:3px;color:{cat_color};text-transform:uppercase;'
                    f'background:rgba({",".join(str(int(cat_color.lstrip("#")[i:i+2], 16)) for i in (0,2,4))},0.12);'
                    f'">{ev["ticker"]}</span></div>'
                    f'<div style="flex:1;">'
                    f'<div style="font-size:0.84rem;font-weight:600;color:{TEXT_PRIMARY};">{ev["event"]}</div>'
                    f'<div style="font-size:0.75rem;color:{TEXT_MUTED};margin-top:2px;">{ev["detail"]}</div>'
                    f'</div>'
                    f'<div style="font-size:0.6rem;font-weight:700;padding:2px 6px;border-radius:3px;'
                    f'color:{imp_color};text-transform:uppercase;'
                    f'background:rgba({",".join(str(int(imp_color.lstrip("#")[i:i+2], 16)) for i in (0,2,4))},0.1);'
                    f'">{imp}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            divider()

        # Full calendar grouped by week
        st.markdown(
            f'<div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.1em;'
            f'color:{TEXT_DIM};font-weight:600;margin-bottom:10px;">Full Calendar (90 Days)</div>',
            unsafe_allow_html=True,
        )

        cal_df = pd.DataFrame(cal_events)
        cal_df["date"] = pd.to_datetime(cal_df["date"])
        cal_df["week"] = cal_df["date"].dt.isocalendar().week
        cal_df["date_str"] = cal_df["date"].dt.strftime("%a %b %d")

        display_df = cal_df[["date_str", "ticker", "event", "category", "impact", "detail"]].copy()
        display_df.columns = ["Date", "Ticker", "Event", "Type", "Impact", "Detail"]
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Impact": st.column_config.TextColumn(width="small"),
                "Type": st.column_config.TextColumn(width="small"),
                "Ticker": st.column_config.TextColumn(width="small"),
            },
        )
    else:
        st.markdown(
            alert_card("info", "No Calendar Data",
                       "Click 'Fetch Catalyst Calendar' to scan for upcoming events.",
                       "Loads earnings dates, ex-dividend dates, and macro releases."),
            unsafe_allow_html=True,
        )
