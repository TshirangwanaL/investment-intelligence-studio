"""Sticky top header bar — app name, environment badge, last refresh."""

from __future__ import annotations

import streamlit as st
from datetime import datetime

from ui.styles import TEXT_PRIMARY, TEXT_DIM, ACCENT, FONT_MONO, BORDER


def render_header(
    title: str = "Investment Intelligence Studio",
) -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(
        f'<div class="t-header">'
        f'<div class="t-header-left">'
        f'<span class="t-header-title">{title}</span>'
        f'<span class="t-badge t-badge-paper" title="No real trades — all data is for analysis only">'
        f'SIMULATION</span>'
        f'</div>'
        f'<div class="t-header-right">'
        f'<span><span class="t-live"></span>CONNECTED</span>'
        f'<span>{now}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
