"""Manage — live per-campaign table with pause / resume / stop."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from auth.gate import gate

me = gate()

from demo_data import demo_ad_account_id, demo_rows
from live_fetcher import fetch_campaigns, pause_campaign, resume_campaign, stop_campaign
from presets import CURRENCY, CURRENCY_CHOICES


st.title("Manage")

ss = st.session_state
ss.setdefault("currency", "USD")
ss.setdefault("ad_account_id", "")
ss.setdefault("demo_mode", True)
ss.setdefault("demo_campaign_status", "ACTIVE")
ss.setdefault("confirm_stop_id", None)


with st.sidebar:
    ss.currency = st.radio("Currency", CURRENCY_CHOICES, horizontal=True, index=CURRENCY_CHOICES.index(ss.currency))
    sym = CURRENCY[ss.currency]["symbol"]
    st.divider()
    ss.demo_mode = st.toggle("Demo mode", value=ss.demo_mode)
    if ss.demo_mode:
        st.caption("Fake data — pause / resume update locally.")
    st.divider()
    st.subheader("Account")
    if ss.demo_mode:
        st.text_input("Ad Account ID", value=demo_ad_account_id(ss.currency), disabled=True)
    else:
        ad_account = st.text_input("Ad Account ID", value=ss.ad_account_id, placeholder="123456789012345")
        ss.ad_account_id = ad_account.strip()
    lookback = st.selectbox("Window", ["today", "yesterday", "last_7d", "last_14d", "last_30d", "this_month"], index=4)


@st.cache_data(ttl=60, show_spinner="Loading campaigns…")
def _cached(ad_account_id: str, window: str):
    return fetch_campaigns(ad_account_id, lookback=window)


if ss.demo_mode:
    rows = demo_rows(currency=ss.currency, status=ss.demo_campaign_status)
else:
    if not ss.ad_account_id:
        st.info("Enter an Ad Account ID in the sidebar.")
        st.stop()
    try:
        rows = _cached(ss.ad_account_id, lookback)
    except Exception as e:
        st.error(str(e))
        st.stop()

if not rows:
    st.info("No campaigns in this window.")
    st.stop()


_PILL = {"ACTIVE": "🟢", "PAUSED": "⏸️", "DELETED": "⛔", "ARCHIVED": "📦", "UNKNOWN": "⚪"}


def _fmt_money(v):
    return "—" if v is None else f"{sym}{v:,.2f}"


def _fmt_pct(v):
    return "—" if v is None else f"{v * 100:.2f}%"


def _fmt_x(v):
    return "—" if v is None else f"{v:.2f}×"


st.caption(f"{len(rows)} campaign(s) · window: {lookback.replace('_', ' ')}")

header = st.columns([3, 1.4, 1, 1, 1, 1, 1, 1, 1.8])
for col, label in zip(header, ["Campaign", "Status", "Spend", "Clicks", "CTR", "Conv.", "CAC", "ROAS", "Actions"]):
    col.markdown(f"**{label}**")
st.divider()

for row in rows:
    cols = st.columns([3, 1.4, 1, 1, 1, 1, 1, 1, 1.8])
    cols[0].markdown(f"**{row.name}**  \n`{row.destination}` · id `{row.campaign_id}`")
    cols[1].markdown(f"{_PILL.get(row.status, '⚪')} {row.status.title()}")
    cols[2].markdown(_fmt_money(row.spend))
    cols[3].markdown(f"{row.clicks:,}")
    cols[4].markdown(_fmt_pct(row.ctr))
    cols[5].markdown(f"{row.conversions:.0f}")
    cols[6].markdown(_fmt_money(row.cac))
    cols[7].markdown(_fmt_x(row.roas) if row.roas else "—")

    with cols[8]:
        a, b, c = st.columns(3)
        if row.status == "ACTIVE":
            if a.button("⏸️", key=f"pause-{row.campaign_id}", help="Pause"):
                if ss.demo_mode:
                    ss.demo_campaign_status = "PAUSED"
                    st.rerun()
                else:
                    try:
                        pause_campaign(row.campaign_id)
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        elif row.status == "PAUSED":
            if b.button("▶️", key=f"resume-{row.campaign_id}", help="Resume"):
                if ss.demo_mode:
                    ss.demo_campaign_status = "ACTIVE"
                    st.rerun()
                else:
                    try:
                        resume_campaign(row.campaign_id)
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if row.status not in ("DELETED", "ARCHIVED"):
            if c.button("✕", key=f"stop-{row.campaign_id}", help="Stop (permanent)"):
                ss.confirm_stop_id = row.campaign_id

    if not ss.demo_mode and row.status == "ACTIVE" and row.destination == "Website" and row.clicks > 100 and row.conversions == 0:
        st.caption(f"  ⚠️ {row.name}: clicks but no conversions — verify Pixel is installed.")


if ss.confirm_stop_id:
    matching = next((r for r in rows if r.campaign_id == ss.confirm_stop_id), None)
    if matching:
        with st.container(border=True):
            st.warning(f"**Stop `{matching.name}`?** This is permanent.")
            c1, c2 = st.columns(2)
            if c1.button("Yes, stop it", type="primary"):
                if ss.demo_mode:
                    ss.demo_campaign_status = "DELETED"
                    ss.confirm_stop_id = None
                    st.rerun()
                else:
                    try:
                        stop_campaign(matching.campaign_id)
                        ss.confirm_stop_id = None
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            if c2.button("Cancel"):
                ss.confirm_stop_id = None
                st.rerun()
