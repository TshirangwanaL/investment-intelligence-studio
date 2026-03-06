"""Central dark-mode stylesheet — Institutional Research Terminal.

Color system:
  bg-base:      #0f1117   (charcoal)
  bg-panel:     #1a1d29   (slate)
  bg-card:      #21242f   (elevated)
  bg-hover:     #282c3a   (interactive)
  border:       #2a2d3a   (subtle)
  border-focus: #3d4150   (active)
  text-primary: #e8eaed   (off-white)
  text-muted:   #9ca3af   (gray-400)
  text-dim:     #6b7280   (gray-500)
  accent:       #5b9bd5   (muted blue)
  accent-dim:   #3d6d99   (dark blue)
  positive:     #4ade80   (green-400)
  warning:      #fbbf24   (amber-400)
  danger:       #f87171   (red-400)
  mono-font:    'JetBrains Mono', 'Cascadia Mono', 'Fira Code', monospace
"""

from __future__ import annotations

import streamlit as st

# ── Color tokens (importable by components) ───────────────────────────

BG_BASE = "#0f1117"
BG_PANEL = "#1a1d29"
BG_CARD = "#21242f"
BG_HOVER = "#282c3a"
BORDER = "#2a2d3a"
BORDER_FOCUS = "#3d4150"
TEXT_PRIMARY = "#e8eaed"
TEXT_MUTED = "#9ca3af"
TEXT_DIM = "#6b7280"
ACCENT = "#5b9bd5"
ACCENT_DIM = "#3d6d99"
POSITIVE = "#4ade80"
WARNING = "#fbbf24"
DANGER = "#f87171"

FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', 'Cascadia Mono', 'Fira Code', 'Consolas', monospace"

# Plotly layout defaults (dark mode)
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT_MUTED, size=11),
    margin=dict(l=10, r=10, t=36, b=10),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER_FOCUS),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER_FOCUS),
)

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Base overrides ────────────────────────────────────────────── */
    .stApp {
        font-family: %(sans)s;
        background: %(bg_base)s;
    }
    .stApp > header { background: transparent !important; }

    /* ── Sidebar ───────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: %(bg_panel)s;
        border-right: 1px solid %(border)s;
    }
    section[data-testid="stSidebar"] * {
        color: %(text_muted)s;
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: %(text_primary)s;
    }

    /* ── Typography ────────────────────────────────────────────────── */
    h1, h2, h3, h4 { color: %(text_primary)s !important; letter-spacing: -0.01em; }
    p, li, span, label, .stMarkdown { color: %(text_muted)s; }
    code, .mono { font-family: %(mono)s !important; font-size: 0.85em; }

    /* ── Panel / Card ──────────────────────────────────────────────── */
    .t-panel {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 20px 24px;
        margin: 6px 0;
    }
    .t-panel-flush { padding: 0; overflow: hidden; }

    /* ── KPI Card ──────────────────────────────────────────────────── */
    .t-kpi {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 16px 20px;
        margin: 4px 0;
    }
    .t-kpi:hover { border-color: %(border_focus)s; }
    .t-kpi-label {
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: %(text_dim)s;
        margin-bottom: 4px;
    }
    .t-kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: %(text_primary)s;
        font-family: %(mono)s;
        line-height: 1.25;
    }
    .t-kpi-delta { font-size: 0.75rem; font-weight: 500; margin-top: 2px; }
    .t-kpi-pos { color: %(positive)s; }
    .t-kpi-neg { color: %(danger)s; }
    .t-kpi-neutral { color: %(text_dim)s; }

    /* ── Alert / Status ────────────────────────────────────────────── */
    .t-alert {
        border-radius: 4px;
        padding: 14px 18px;
        margin: 6px 0;
        border-left: 3px solid %(border)s;
        background: %(bg_card)s;
    }
    .t-alert-critical { border-left-color: %(danger)s; background: rgba(248,113,113,0.06); }
    .t-alert-warning  { border-left-color: %(warning)s; background: rgba(251,191,36,0.06); }
    .t-alert-info     { border-left-color: %(accent)s;  background: rgba(91,155,213,0.06); }
    .t-alert-success  { border-left-color: %(positive)s; background: rgba(74,222,128,0.06); }
    .t-alert-title { font-weight: 600; color: %(text_primary)s; margin-bottom: 4px; font-size: 0.9rem; }
    .t-alert-body { font-size: 0.85rem; color: %(text_muted)s; }
    .t-alert-hint { font-size: 0.75rem; color: %(text_dim)s; margin-top: 6px; font-style: italic; }

    /* ── Badge ─────────────────────────────────────────────────────── */
    .t-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 3px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-family: %(mono)s;
    }
    .t-badge-paper   { background: rgba(91,155,213,0.15); color: %(accent)s; border: 1px solid %(accent_dim)s; }
    .t-badge-pos     { background: rgba(74,222,128,0.12); color: %(positive)s; }
    .t-badge-neg     { background: rgba(248,113,113,0.12); color: %(danger)s; }
    .t-badge-warn    { background: rgba(251,191,36,0.12); color: %(warning)s; }
    .t-badge-neutral { background: rgba(156,163,175,0.12); color: %(text_muted)s; }

    /* ── Vote ──────────────────────────────────────────────────────── */
    .t-vote {
        display: inline-block;
        padding: 6px 20px;
        border-radius: 3px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        font-family: %(mono)s;
    }
    .t-vote-buy  { background: rgba(74,222,128,0.15); color: %(positive)s; border: 1px solid %(positive)s; }
    .t-vote-hold { background: rgba(251,191,36,0.15);  color: %(warning)s;  border: 1px solid %(warning)s; }
    .t-vote-sell { background: rgba(248,113,113,0.15); color: %(danger)s;   border: 1px solid %(danger)s; }

    /* ── Thesis card ───────────────────────────────────────────────── */
    .t-thesis {
        background: %(bg_card)s;
        border: 1px solid %(border)s;
        border-radius: 6px;
        padding: 20px 24px;
        margin: 8px 0;
    }
    .t-thesis-bull { border-top: 2px solid %(positive)s; }
    .t-thesis-bear { border-top: 2px solid %(danger)s; }

    /* ── Table (dense, zebra rows) ─────────────────────────────────── */
    .stDataFrame, .stTable {
        font-size: 0.82rem !important;
    }
    [data-testid="stDataFrame"] th {
        background: %(bg_panel)s !important;
        color: %(text_dim)s !important;
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        border-bottom: 1px solid %(border)s !important;
    }
    [data-testid="stDataFrame"] td {
        font-family: %(mono)s !important;
        font-size: 0.8rem !important;
        border-bottom: 1px solid %(border)s !important;
    }

    /* ── Tabs ──────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 1px solid %(border)s;
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.8rem;
        font-weight: 500;
        color: %(text_dim)s;
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: %(accent)s !important;
        border-bottom-color: %(accent)s !important;
    }

    /* ── Buttons ───────────────────────────────────────────────────── */
    .stButton > button {
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.82rem;
        letter-spacing: 0.02em;
        transition: all 0.15s ease;
        border: 1px solid %(border_focus)s !important;
        color: %(text_primary)s !important;
        background: %(bg_card)s !important;
    }
    .stButton > button:hover {
        background: %(bg_hover)s !important;
        border-color: %(accent)s !important;
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stFormSubmitButton"] > button,
    .stFormSubmitButton > button {
        background: %(accent)s !important;
        color: #fff !important;
        border: 1px solid %(accent)s !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover {
        background: %(accent_dim)s !important;
        border-color: %(accent_dim)s !important;
    }
    .stFormSubmitButton > button {
        background: %(accent)s !important;
        color: #fff !important;
        border: 1px solid %(accent)s !important;
        font-weight: 600;
    }

    /* ── Timeline ──────────────────────────────────────────────────── */
    .t-timeline {
        border-left: 2px solid %(border)s;
        padding: 10px 0 10px 20px;
        margin-left: 8px;
        position: relative;
    }
    .t-timeline::before {
        content: '';
        width: 8px; height: 8px;
        background: %(accent)s;
        border-radius: 50%%;
        position: absolute;
        left: -5px; top: 14px;
    }

    /* ── Divider ───────────────────────────────────────────────────── */
    .t-divider {
        height: 1px;
        background: %(border)s;
        margin: 20px 0;
    }

    /* ── Confidence bar ────────────────────────────────────────────── */
    .t-conf-track {
        background: %(bg_panel)s;
        border-radius: 3px;
        height: 6px;
        overflow: hidden;
    }
    .t-conf-fill {
        height: 100%%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    /* ── Header bar ────────────────────────────────────────────────── */
    .t-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0;
        margin-bottom: 16px;
        border-bottom: 1px solid %(border)s;
    }
    .t-header-left { display: flex; align-items: center; gap: 12px; }
    .t-header-title {
        font-size: 1rem;
        font-weight: 700;
        color: %(text_primary)s;
        letter-spacing: -0.01em;
    }
    .t-header-right {
        display: flex;
        align-items: center;
        gap: 16px;
        font-size: 0.72rem;
        color: %(text_dim)s;
        font-family: %(mono)s;
    }

    /* ── Pulse dot ─────────────────────────────────────────────────── */
    @keyframes t-pulse {
        0%%, 100%% { opacity: 1; }
        50%% { opacity: 0.4; }
    }
    .t-live {
        display: inline-block;
        width: 6px; height: 6px;
        background: %(positive)s;
        border-radius: 50%%;
        margin-right: 5px;
        animation: t-pulse 2s infinite;
    }

    /* ── Cleanup ────────────────────────────────────────────────────── */
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    #MainMenu { visibility: hidden; }
</style>
""" % {
    "sans": FONT_SANS, "mono": FONT_MONO,
    "bg_base": BG_BASE, "bg_panel": BG_PANEL, "bg_card": BG_CARD,
    "bg_hover": BG_HOVER, "border": BORDER, "border_focus": BORDER_FOCUS,
    "text_primary": TEXT_PRIMARY, "text_muted": TEXT_MUTED, "text_dim": TEXT_DIM,
    "accent": ACCENT, "accent_dim": ACCENT_DIM,
    "positive": POSITIVE, "warning": WARNING, "danger": DANGER,
}


def inject() -> None:
    """Inject the institutional dark theme CSS into the page."""
    st.markdown(CSS, unsafe_allow_html=True)
