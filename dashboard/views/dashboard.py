"""Dashboard view — KPI grid + running campaigns + benchmark report."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from auth.gate import gate

# Enforce auth + active subscription. Returns user dict.
me = gate()

from benchmark_bridge import run_benchmark, summary_lines
from demo_data import demo_ad_account_id, demo_rows
from live_fetcher import fetch_account_totals, fetch_campaigns
from presets import CURRENCY, CURRENCY_CHOICES
from styles import hero, inject_css, status_pill

inject_css()


ss = st.session_state
ss.setdefault("currency", "USD")
ss.setdefault("ad_account_id", "")
ss.setdefault("demo_mode", True)
ss.setdefault("demo_campaign_status", "ACTIVE")


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("**Workspace**")
    ss.currency = st.radio("Currency", CURRENCY_CHOICES, horizontal=True, index=CURRENCY_CHOICES.index(ss.currency))
    sym = CURRENCY[ss.currency]["symbol"]
    st.divider()

    ss.demo_mode = st.toggle("Demo mode", value=ss.demo_mode)
    if ss.demo_mode:
        st.caption(f"Showing sample data in {ss.currency}.")
    st.divider()

    st.markdown("**Account**")
    if ss.demo_mode:
        st.text_input("Ad Account ID", value=demo_ad_account_id(ss.currency), disabled=True)
    else:
        ad_account = st.text_input("Ad Account ID", value=ss.ad_account_id, placeholder="123456789012345")
        ss.ad_account_id = ad_account.strip()

    lookback = st.selectbox(
        "Window",
        ["today", "yesterday", "last_7d", "last_14d", "last_30d", "this_month"],
        index=4,
    )


# ---------- Hero ----------
hero(
    "Dashboard",
    kicker=f"Signed in as {me['email']}",
    subtitle="Live KPIs from your connected Meta Ad Account. Switch demo mode off in the sidebar to load real data.",
)


@st.cache_data(ttl=60, show_spinner="Loading…")
def _cached_rows(ad_account_id: str, window: str):
    return fetch_campaigns(ad_account_id, lookback=window)


if ss.demo_mode:
    rows = demo_rows(currency=ss.currency, status=ss.demo_campaign_status)
else:
    if not ss.ad_account_id:
        st.info("Add an Ad Account ID in the sidebar to load live KPIs.")
        st.stop()
    try:
        rows = _cached_rows(ss.ad_account_id, lookback)
    except Exception as e:
        st.error(str(e))
        st.stop()

totals = fetch_account_totals(rows)


# ---------- Formatters ----------
def _fmt_money(v: float | None) -> str:
    return "—" if v is None else f"{sym}{v:,.2f}"


def _fmt_x(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f}×"


def _fmt_pct(v: float | None) -> str:
    return "—" if v is None else f"{v * 100:.2f}%"


# ---------- KPI grid ----------
g1, g2, g3, g4 = st.columns(4)
g1.metric("Spend", _fmt_money(totals["spend"]))
g2.metric("Reach", f"{totals['reach']:,}")
g3.metric("Clicks", f"{totals['clicks']:,}")
g4.metric("CTR", _fmt_pct(totals["ctr"]))

g5, g6, g7, g8 = st.columns(4)
g5.metric("Avg CPC", _fmt_money(totals["avg_cpc"]))
g6.metric("Conversions", f"{totals['conversions']:.0f}")
g7.metric("CAC", _fmt_money(totals["cac"]))
g8.metric("ROAS", _fmt_x(totals["roas"]) if totals["roas"] else "—")

st.caption(
    f"{totals['active_count']} active of {totals['campaign_count']} · "
    f"window: {lookback.replace('_', ' ')}"
)


# ---------- Health banners ----------
website_zero_conv = any(
    r.destination == "Website" and r.clicks > 100 and r.conversions == 0
    for r in rows
)
if not ss.demo_mode and website_zero_conv:
    st.warning(
        "Website ad has clicks but no conversions. "
        "Install Meta Pixel + Purchase event on the landing page to track CAC / ROAS, "
        "or run an Instant Form ad instead (native conversion tracking)."
    )


st.divider()


# ---------- Running table ----------
st.subheader("Running campaigns")
if not rows:
    st.info("No campaigns in this window.")
else:
    # Build an HTML-friendly row set so we can render status as a pill (no emoji).
    data = [
        {
            "Campaign": r.name,
            "Destination": r.destination,
            "Status": r.status.title(),
            "Spend": r.spend,
            "Clicks": r.clicks,
            "CTR": r.ctr,
            "Conv.": r.conversions,
            "CAC": r.cac,
            "ROAS": r.roas,
        }
        for r in rows
    ]
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Spend": st.column_config.NumberColumn(format=f"{sym}%.2f"),
            "Clicks": st.column_config.NumberColumn(format="%d"),
            "CTR": st.column_config.NumberColumn(format="%.2f%%"),
            "Conv.": st.column_config.NumberColumn(format="%.0f"),
            "CAC": st.column_config.NumberColumn(format=f"{sym}%.2f"),
            "ROAS": st.column_config.NumberColumn(format="%.2f×"),
        },
    )

    # Status pills underneath — gives a clean colour-dot view per campaign.
    pill_html = " &nbsp; ".join(
        f"<span style='font-size:12px;color:#54595F;margin-right:4px;'>{r.name[:32]}</span>"
        f"{status_pill(r.status)}"
        for r in rows
    )
    st.markdown(
        f"<div style='margin-top:6px;'>{pill_html}</div>",
        unsafe_allow_html=True,
    )


st.divider()
with st.expander("Benchmark report", expanded=False):
    if ss.demo_mode:
        st.caption("Benchmark uses the live account; available once Demo mode is off.")
    else:
        bench_window = st.selectbox("Lookback (days)", [7, 30, 90], index=1, key="bench_lookback")
        if st.button("Run benchmark", type="primary"):
            try:
                with st.spinner("Running benchmark…"):
                    report = run_benchmark(
                        ad_account_id=ss.ad_account_id,
                        lookback_days=int(bench_window),
                    )
                ss["meta_benchmark_report"] = report
            except Exception as e:
                st.error(str(e))
        report = ss.get("meta_benchmark_report")
        if report:
            for line in summary_lines(report):
                st.markdown(f"- {line}")
            with st.expander("Raw JSON"):
                st.json(report)
