"""Reusable UI components for the Institutional Research Terminal."""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from typing import Any

from ui.styles import (
    BG_BASE, BG_PANEL, BG_CARD, BG_HOVER, BORDER, BORDER_FOCUS,
    TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, ACCENT, ACCENT_DIM,
    POSITIVE, WARNING, DANGER, FONT_SANS, FONT_MONO, PLOTLY_LAYOUT,
)


# ── KPI Card ──────────────────────────────────────────────────────────

def kpi_card(label: str, value: str, delta: str = "", delta_type: str = "neutral") -> str:
    delta_cls = f"t-kpi-{delta_type}"
    delta_html = f'<div class="{delta_cls}">{delta}</div>' if delta else ""
    return (
        f'<div class="t-kpi">'
        f'<div class="t-kpi-label">{label}</div>'
        f'<div class="t-kpi-value">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def render_kpi_row(kpis: list[tuple[str, str, str, str]]) -> None:
    """Render KPI cards in a row. Each tuple: (label, value, delta, delta_type)."""
    cols = st.columns(len(kpis))
    for col, (label, value, delta, dtype) in zip(cols, kpis):
        with col:
            st.markdown(kpi_card(label, value, delta, dtype), unsafe_allow_html=True)


# ── Alert Card ────────────────────────────────────────────────────────

def alert_card(severity: str, title: str, message: str, hint: str = "") -> str:
    icon = {"critical": "!!", "warning": "!", "info": "i", "success": "OK"}.get(severity, "i")
    hint_html = f'<div class="t-alert-hint">{hint}</div>' if hint else ""
    return (
        f'<div class="t-alert t-alert-{severity}">'
        f'<div class="t-alert-title">[{icon}] {title}</div>'
        f'<div class="t-alert-body">{message}</div>'
        f'{hint_html}'
        f'</div>'
    )


# ── Badge ─────────────────────────────────────────────────────────────

def badge(text: str, variant: str = "neutral") -> str:
    return f'<span class="t-badge t-badge-{variant}">{text}</span>'


# ── Vote Badge ────────────────────────────────────────────────────────

def vote_badge(vote: str) -> str:
    v = vote.lower().strip()
    cls = {"buy": "t-vote-buy", "hold": "t-vote-hold", "sell": "t-vote-sell"}.get(v, "t-vote-hold")
    return f'<span class="t-vote {cls}">{vote.upper()}</span>'


# ── Confidence Bar ────────────────────────────────────────────────────

def confidence_bar(confidence: float, label: str = "") -> None:
    pct = int(confidence * 100)
    if confidence >= 0.75:
        color = POSITIVE
    elif confidence >= 0.50:
        color = WARNING
    else:
        color = DANGER
    label_html = f'<span style="font-size:0.72rem;color:{TEXT_DIM};">{label}</span>' if label else ""
    html = (
        f'<div style="margin:6px 0;">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
        f'{label_html}'
        f'<span style="font-size:0.72rem;color:{color};font-family:{FONT_MONO};font-weight:600;">{pct}%</span>'
        f'</div>'
        f'<div class="t-conf-track">'
        f'<div class="t-conf-fill" style="background:{color};width:{pct}%;"></div>'
        f'</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def confidence_badge_html(confidence: float) -> str:
    pct = f"{confidence:.0%}"
    if confidence >= 0.75:
        variant = "pos"
    elif confidence >= 0.50:
        variant = "warn"
    else:
        variant = "neg"
    return badge(pct, variant)


# ── Panel ─────────────────────────────────────────────────────────────

def panel(content_html: str, flush: bool = False) -> None:
    cls = "t-panel t-panel-flush" if flush else "t-panel"
    st.markdown(f'<div class="{cls}">{content_html}</div>', unsafe_allow_html=True)


def panel_header(title: str, right_html: str = "") -> None:
    right = f'<span style="font-size:0.72rem;color:{TEXT_DIM};font-family:{FONT_MONO};">{right_html}</span>'
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid {BORDER};">'
        f'<span style="font-size:0.85rem;font-weight:600;color:{TEXT_PRIMARY};letter-spacing:-0.01em;">'
        f'{title}</span>{right}</div>',
        unsafe_allow_html=True,
    )


# ── Divider ───────────────────────────────────────────────────────────

def divider() -> None:
    st.markdown('<div class="t-divider"></div>', unsafe_allow_html=True)


# ── Live Dot ──────────────────────────────────────────────────────────

def live_dot(text: str = "Live") -> str:
    return f'<span><span class="t-live"></span>{text}</span>'


# ── Health Score ──────────────────────────────────────────────────────

def portfolio_health_score(
    n_positions: int,
    cash_weight: float,
    top5_conc: float,
    constraint_violations: int,
    has_thesis: bool = False,
) -> tuple[int, str]:
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
    if score >= 80:
        bar_color = POSITIVE
    elif score >= 60:
        bar_color = WARNING
    else:
        bar_color = DANGER

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "", "font": {"size": 42, "family": "Inter", "color": TEXT_PRIMARY}},
        title={"text": f"Portfolio Health \u2014 {label}",
               "font": {"size": 12, "family": "Inter", "color": TEXT_DIM}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "dtick": 25,
                     "tickfont": {"size": 9, "color": TEXT_DIM}},
            "bar": {"color": bar_color, "thickness": 0.7},
            "bgcolor": BG_PANEL,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "rgba(248,113,113,0.08)"},
                {"range": [40, 60], "color": "rgba(251,191,36,0.08)"},
                {"range": [60, 80], "color": "rgba(74,222,128,0.05)"},
                {"range": [80, 100], "color": "rgba(74,222,128,0.10)"},
            ],
            "threshold": {
                "line": {"color": TEXT_MUTED, "width": 2},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=200,
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Charts ────────────────────────────────────────────────────────────

_PALETTE = [
    ACCENT, POSITIVE, WARNING, DANGER, "#a78bfa", "#38bdf8",
    "#f472b6", "#84cc16", "#fb923c", "#818cf8", "#2dd4bf", "#e879f9",
]


def render_donut(
    labels: list[str], values: list[float], title: str = "", height: int = 280,
) -> None:
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.58,
        marker=dict(colors=_PALETTE[: len(labels)], line=dict(color=BG_BASE, width=2)),
        textinfo="label+percent",
        textfont=dict(size=10, family="Inter", color=TEXT_MUTED),
        hoverinfo="label+value+percent",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, family="Inter", color=TEXT_MUTED)),
        height=height,
        showlegend=False,
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_hbar(
    labels: list[str], values: list[float], title: str = "",
    height: int = 250, color_by_sign: bool = True,
) -> None:
    colors = [(POSITIVE if v >= 0 else DANGER) for v in values] if color_by_sign else [ACCENT] * len(values)
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors, cornerradius=3),
        text=[f"{v:+.2f}" for v in values],
        textposition="outside",
        textfont=dict(size=10, family="Inter", color=TEXT_MUTED),
    ))
    base = {k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")}
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, family="Inter", color=TEXT_MUTED)),
        height=height,
        **base,
        yaxis=dict(automargin=True, gridcolor=BORDER),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=True,
                   zerolinecolor=BORDER_FOCUS, zerolinewidth=1),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Workflow Steps ────────────────────────────────────────────────────

def render_workflow_steps(steps: list[tuple[str, str]], current: int = 0) -> None:
    cols = st.columns(len(steps))
    for i, (col, (name, status)) in enumerate(zip(cols, steps)):
        with col:
            if status == "done":
                color, icon = POSITIVE, "+"
            elif status == "active":
                color, icon = ACCENT, ">"
            else:
                color, icon = TEXT_DIM, "-"
            st.markdown(
                f'<div style="text-align:center;">'
                f'<div style="width:24px;height:24px;border-radius:50%;margin:0 auto 4px;'
                f'background:rgba({_hex_to_rgb(color)},0.15);color:{color};'
                f'font-size:0.75rem;font-weight:700;line-height:24px;font-family:{FONT_MONO};">'
                f'{icon}</div>'
                f'<div style="font-size:0.65rem;color:{color};font-weight:500;">{name}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"
