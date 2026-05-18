"""Login + Signup page. Entry point when not authenticated."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from auth import auth as auth_mod
from auth.subscription import PRICING, WHATSAPP_NUMBER
from styles import hero, inject_css

inject_css()


# Already logged in? Bounce to the dashboard.
if auth_mod.current_user():
    try:
        st.switch_page("views/dashboard.py")
    except Exception:
        st.info("You're already signed in.")
    st.stop()


hero(
    "Meta Ads Launcher",
    kicker="Welcome",
    subtitle="Launch and manage Facebook + Instagram ad campaigns for your clients — built for solo operators and small agencies.",
)

login_tab, signup_tab = st.tabs(["Sign in", "Create account"])


with login_tab:
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submit:
        try:
            user = auth_mod.login(email, password)
            auth_mod.set_session(user["id"])
            st.success("Signed in. Redirecting…")
            try:
                st.switch_page("views/dashboard.py")
            except Exception:
                st.rerun()
        except auth_mod.AuthError as e:
            st.error(str(e))


with signup_tab:
    st.markdown(
        '<div style="color:#54595F;margin-bottom:8px;">'
        'Start with a <strong>2-day free trial</strong>. '
        'No card required.'
        '</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    inr_box = cols[0].container(border=True)
    usd_box = cols[1].container(border=True)
    inr_box.markdown(
        f"<div style='font-size:22px;font-weight:700;'>"
        f"{PRICING['INR']['currency_symbol']}{PRICING['INR']['amount']}"
        f"<span style='font-size:13px;font-weight:500;color:#54595F;'> / month</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    inr_box.caption("India · UPI · cards · NetBanking via Razorpay")
    inr_box.caption("Starter: 1 client account · Meta + Instagram")

    usd_box.markdown(
        f"<div style='font-size:22px;font-weight:700;'>"
        f"{PRICING['USD']['currency_symbol']}{PRICING['USD']['amount']}"
        f"<span style='font-size:13px;font-weight:500;color:#54595F;'> / month</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    usd_box.caption("International · cards via Razorpay")
    usd_box.caption("Starter: 1 client account · Meta + Instagram")

    st.caption(
        f"Need 5+ clients? Agency plans start at ₹3,499/mo · "
        f"WhatsApp {WHATSAPP_NUMBER}"
    )
    st.divider()

    with st.form("signup_form", clear_on_submit=False):
        email = st.text_input("Email")
        password = st.text_input("Password (min 8 chars)", type="password")
        currency = st.radio(
            "I'm based in",
            ["INR", "USD"],
            format_func=lambda c: "India (₹999/mo)" if c == "INR" else "Elsewhere ($21/mo)",
            horizontal=True,
        )
        submit = st.form_submit_button("Start free trial", type="primary", use_container_width=True)
    if submit:
        try:
            user_id = auth_mod.signup(email, password, currency=currency)
            auth_mod.set_session(user_id)
            st.success("Account created. Trial started.")
            try:
                st.switch_page("views/dashboard.py")
            except Exception:
                st.rerun()
        except auth_mod.AuthError as e:
            st.error(str(e))
