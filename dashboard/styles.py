"""Shared visual language — global CSS + helpers.

Every view calls `inject_css()` once at the top, then uses `hero()` for the
page header and `status_pill()` for status badges. No emojis anywhere; status
gets a colored dot drawn in CSS.
"""
from __future__ import annotations

import streamlit as st


_BRAND_PRIMARY = "#1877F2"
_BRAND_PRIMARY_DARK = "#3856A8"
_INK = "#1C1E21"
_INK_SOFT = "#54595F"
_SURFACE = "#FFFFFF"
_SURFACE_SOFT = "#F4F6F8"
_BORDER = "#E4E6EB"
_OK = "#16A34A"
_WARN = "#D97706"
_ERR = "#DC2626"
_MUTED = "#94A3B8"


_GLOBAL_CSS = f"""
<style>
  /* ----- Base typography ----- */
  html, body, [data-testid="stAppViewContainer"] {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                   "Helvetica Neue", Arial, sans-serif;
      color: {_INK};
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
  }}

  h1, h2, h3, h4 {{
      letter-spacing: -0.01em;
      font-weight: 600;
  }}

  /* Quieter section labels rendered via st.subheader */
  h2, h3 {{
      margin-top: 0.4rem;
      margin-bottom: 0.6rem;
  }}

  /* ----- Primary button ----- */
  div.stButton > button[kind="primary"],
  div.stDownloadButton > button[kind="primary"],
  div.stFormSubmitButton > button[kind="primary"] {{
      background: linear-gradient(135deg, {_BRAND_PRIMARY} 0%, {_BRAND_PRIMARY_DARK} 100%);
      border: none;
      color: white;
      font-weight: 600;
      letter-spacing: 0.01em;
      padding: 0.55rem 1.1rem;
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(24,119,242,0.18), 0 4px 14px rgba(24,119,242,0.12);
      transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
  }}
  div.stButton > button[kind="primary"]:hover,
  div.stDownloadButton > button[kind="primary"]:hover,
  div.stFormSubmitButton > button[kind="primary"]:hover {{
      transform: translateY(-1px);
      filter: brightness(1.04);
      box-shadow: 0 3px 6px rgba(24,119,242,0.22), 0 10px 22px rgba(24,119,242,0.18);
  }}
  div.stButton > button[kind="primary"]:active {{
      transform: translateY(0);
      filter: brightness(0.96);
  }}

  /* ----- Secondary button ----- */
  div.stButton > button:not([kind="primary"]),
  div.stDownloadButton > button:not([kind="primary"]),
  div.stFormSubmitButton > button:not([kind="primary"]) {{
      background: {_SURFACE};
      color: {_INK};
      border: 1px solid {_BORDER};
      font-weight: 500;
      letter-spacing: 0.01em;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      transition: border-color .12s ease, background .12s ease, transform .12s ease;
  }}
  div.stButton > button:not([kind="primary"]):hover,
  div.stDownloadButton > button:not([kind="primary"]):hover,
  div.stFormSubmitButton > button:not([kind="primary"]):hover {{
      border-color: {_BRAND_PRIMARY};
      color: {_BRAND_PRIMARY};
      background: rgba(24,119,242,0.04);
  }}

  /* ----- Inputs ----- */
  input, textarea, [data-baseweb="input"], [data-baseweb="select"] > div,
  [data-baseweb="textarea"] {{
      border-radius: 8px !important;
      transition: border-color .12s ease, box-shadow .12s ease;
  }}
  input:focus, textarea:focus {{
      box-shadow: 0 0 0 3px rgba(24,119,242,0.15) !important;
  }}
  [data-testid="stTextInput"] label,
  [data-testid="stTextArea"] label,
  [data-testid="stSelectbox"] label,
  [data-testid="stMultiSelect"] label,
  [data-testid="stRadio"] label,
  [data-testid="stNumberInput"] label,
  [data-testid="stFileUploader"] label {{
      font-weight: 500;
      color: {_INK_SOFT};
      font-size: 0.86rem;
      letter-spacing: 0.01em;
  }}

  /* ----- Radio + toggle pills ----- */
  [data-testid="stRadio"] [role="radiogroup"] label {{
      transition: background .12s ease, border-color .12s ease;
  }}

  /* ----- Tabs ----- */
  div[data-baseweb="tab-list"] button[data-baseweb="tab"] {{
      font-weight: 500;
      letter-spacing: 0.01em;
      transition: color .12s ease;
  }}
  div[data-baseweb="tab-list"] button[aria-selected="true"] {{
      color: {_BRAND_PRIMARY};
      font-weight: 600;
  }}
  div[data-baseweb="tab-highlight"] {{
      background: {_BRAND_PRIMARY};
      height: 3px;
  }}

  /* ----- Cards (st.container(border=True)) ----- */
  [data-testid="stVerticalBlockBorderWrapper"] {{
      border-radius: 12px !important;
      border-color: {_BORDER} !important;
      box-shadow: 0 1px 2px rgba(16,24,40,0.04);
      transition: box-shadow .15s ease, transform .15s ease;
  }}
  [data-testid="stVerticalBlockBorderWrapper"]:hover {{
      box-shadow: 0 2px 6px rgba(16,24,40,0.07);
  }}

  /* ----- Metric ----- */
  [data-testid="stMetricLabel"] {{
      color: {_INK_SOFT};
      font-weight: 500;
      letter-spacing: 0.01em;
      font-size: 0.85rem;
  }}
  [data-testid="stMetricValue"] {{
      font-weight: 700;
      letter-spacing: -0.02em;
  }}

  /* ----- Dataframe ----- */
  [data-testid="stDataFrame"] {{
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid {_BORDER};
  }}

  /* ----- Top navigation ----- */
  header[data-testid="stHeader"] {{
      background: {_SURFACE};
      border-bottom: 1px solid {_BORDER};
  }}
  [data-testid="stToolbar"] a, [data-testid="stToolbar"] button {{
      color: {_INK_SOFT};
  }}

  /* ----- Alerts ----- */
  [data-testid="stAlert"] {{
      border-radius: 10px;
      border-width: 1px;
  }}

  /* ----- Captions / muted text ----- */
  [data-testid="stCaptionContainer"], small {{
      color: {_INK_SOFT};
  }}

  /* ----- Sidebar ----- */
  section[data-testid="stSidebar"] {{
      background: {_SURFACE_SOFT};
      border-right: 1px solid {_BORDER};
  }}

  /* ----- Subtle fade-in for content blocks ----- */
  @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .ml-hero, .ml-card, .ml-pill, .ml-stat {{
      animation: fadeUp .25s ease both;
  }}
</style>
"""


def inject_css() -> None:
    """Inject global CSS exactly once per session."""
    if st.session_state.get("_css_injected"):
        return
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    st.session_state["_css_injected"] = True


def hero(title: str, *, kicker: str | None = None, subtitle: str | None = None) -> None:
    """Gradient hero — replaces st.title on every page for visual consistency."""
    kicker_html = (
        f'<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;'
        f'opacity:.85;margin-bottom:6px;">{kicker}</div>'
        if kicker else ""
    )
    subtitle_html = (
        f'<div style="font-size:14px;opacity:.9;margin-top:8px;max-width:720px;">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f"""
        <div class="ml-hero" style="
            background: linear-gradient(135deg, {_BRAND_PRIMARY} 0%, {_BRAND_PRIMARY_DARK} 100%);
            color: white;
            padding: 22px 26px;
            border-radius: 12px;
            margin: 6px 0 18px 0;
            box-shadow: 0 1px 2px rgba(56,86,168,0.18), 0 8px 28px rgba(56,86,168,0.12);
        ">
            {kicker_html}
            <div style="font-size:26px;font-weight:700;line-height:1.15;letter-spacing:-0.01em;">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


_PILL_COLORS = {
    "ACTIVE":   (_OK,    "#DCFCE7"),
    "PAUSED":   (_INK_SOFT, _SURFACE_SOFT),
    "TRIALING": (_BRAND_PRIMARY, "#E6F0FE"),
    "PAST_DUE": (_WARN,  "#FEF3C7"),
    "EXPIRED":  (_ERR,   "#FEE2E2"),
    "CANCELED": (_MUTED, _SURFACE_SOFT),
    "DELETED":  (_ERR,   "#FEE2E2"),
    "ARCHIVED": (_MUTED, _SURFACE_SOFT),
    "UNKNOWN":  (_MUTED, _SURFACE_SOFT),
}


def status_pill(status: str) -> str:
    """Return an inline HTML pill — colored dot + label. No emoji."""
    key = (status or "UNKNOWN").upper()
    fg, bg = _PILL_COLORS.get(key, _PILL_COLORS["UNKNOWN"])
    return (
        f'<span class="ml-pill" style="'
        f'display:inline-flex;align-items:center;gap:6px;'
        f'padding:3px 10px;border-radius:999px;'
        f'background:{bg};color:{fg};font-size:12px;font-weight:600;'
        f'letter-spacing:.02em;">'
        f'<span style="width:6px;height:6px;border-radius:999px;background:{fg};"></span>'
        f'{status.title()}'
        f'</span>'
    )


def section_label(text: str) -> None:
    """Small uppercase eyebrow label above a section."""
    st.markdown(
        f'<div style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;'
        f'color:{_INK_SOFT};font-weight:600;margin:14px 0 6px 0;">{text}</div>',
        unsafe_allow_html=True,
    )
