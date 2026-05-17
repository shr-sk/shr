"""Account view — current plan, billing, upgrade, logout."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from auth import auth as auth_mod
from auth import db, subscription
from auth.subscription import PRICING, WHATSAPP_NUMBER


# Auth gate — but don't enforce active subscription here (this IS the
# upgrade page). Just require login.
me = auth_mod.current_user()
if not me:
    try:
        st.switch_page("views/login.py")
    except Exception:
        st.warning("Please sign in.")
        st.stop()

user_row = db.find_user(me["id"])
sub = db.get_subscription(me["id"]) or {}


st.title("Account")

# ---------- Profile summary ----------
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**Email** · {me['email']}")
    st.markdown(f"**Currency** · {me['currency']}")
    st.markdown(f"**Tier** · `{me['tier']}`")
with c2:
    st.markdown(f"**Client limit** · {me['client_limit']}")
    st.markdown(f"**Team seats** · {me['team_seats']}")
    st.markdown(f"**Member since** · {user_row['created_at'][:10] if user_row else '—'}")


st.divider()

# ---------- Subscription status ----------
st.subheader("Subscription")

status = sub.get("status", "expired")
trial_end = db.parse_iso(user_row.get("trial_ends_at")) if user_row else None
now = datetime.now(timezone.utc)

if status == "trialing":
    days_left = (trial_end - now).days if trial_end else 0
    hours_left = max(0, int((trial_end - now).total_seconds() / 3600)) if trial_end else 0
    if hours_left < 24:
        st.warning(f"⏰ **Trial ends in {hours_left} hours.** Upgrade to keep your campaigns running.")
    else:
        st.info(f"Free trial · {days_left} day(s) remaining")
elif status == "active":
    end = db.parse_iso(sub.get("current_period_end"))
    end_str = end.strftime("%d %b %Y") if end else "—"
    st.success(f"✅ Active · renews {end_str}")
elif status == "past_due":
    st.error("⚠️ Payment failed. Update your payment method to keep your campaigns running.")
elif status == "expired":
    st.error("Subscription expired. Renew below to resume your campaigns.")
elif status == "canceled":
    st.warning("Subscription canceled. Renew below to resume.")

st.divider()


# ---------- Upgrade flow ----------
st.subheader("Upgrade" if status != "active" else "Manage plan")

price = PRICING[me["currency"]]
plan_id = subscription.plan_id_for(me["currency"])

box = st.container(border=True)
with box:
    st.markdown(f"### Starter — {price['currency_symbol']}{price['amount']}/month")
    st.caption("1 client account · Meta + Instagram · Insights · Pause/Resume")

    if subscription.razorpay_configured() and plan_id:
        # Real Razorpay flow
        if st.button("Pay with Razorpay", type="primary", use_container_width=True):
            try:
                with st.spinner("Creating subscription…"):
                    result = subscription.create_subscription(
                        user={"id": me["id"], "email": me["email"], "tier": me["tier"]},
                        plan_id=plan_id,
                    )
                checkout_url = result.get("short_url")
                if checkout_url:
                    st.success("Redirecting to Razorpay…")
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={checkout_url}">',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"[Click here if not redirected]({checkout_url})")
                else:
                    st.error("Could not generate checkout link.")
            except Exception as e:
                st.error(f"Razorpay error: {e}")
    else:
        # Razorpay isn't configured yet — usually because merchant verification
        # is still under review with Razorpay. Show a neutral message that
        # signals our intent to integrate Razorpay (so Razorpay reviewers
        # don't think we're routing around them).
        st.info(
            f"**Subscribe to Starter — {price['currency_symbol']}{price['amount']}/month**  \n"
            "Online subscription billing via Razorpay is being activated. "
            "Once our merchant verification is complete, you'll be able to "
            "subscribe directly from this page."
        )
        st.markdown(
            f"In the meantime, contact us on WhatsApp **{WHATSAPP_NUMBER}** "
            "or email **sukumarpoddar90@gmail.com** to start your subscription."
        )


st.divider()


# ---------- Agency tier ----------
with st.expander("Need 5+ clients? Agency plans"):
    st.markdown(f"""
    **Agency Lite** — up to 5 clients · 1 seat · ₹3,499 / $75 per month
    **Agency Standard** — up to 10 clients · 2 seats · ₹6,499 / $140 per month
    **Agency Pro** — up to 25 clients · 5 seats · ₹14,999 / $325 per month

    For setup, message us on **WhatsApp {WHATSAPP_NUMBER}** with:
    1. Number of clients
    2. Markets (India / USA / both)
    3. Number of team seats needed

    We'll send a Razorpay invoice and activate your account within 24 hours.
    """)


st.divider()

# ---------- Logout ----------
if st.button("Sign out", use_container_width=False):
    auth_mod.clear_session()
    try:
        st.switch_page("views/login.py")
    except Exception:
        st.rerun()
