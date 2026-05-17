"""Account view — current plan, billing, Razorpay subscribe, logout."""
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

# Razorpay redirects back to the app after checkout. Streamlit Cloud strips
# query params on the next rerun, so we read once + show a confirmation.
qp = st.query_params
just_paid = qp.get("razorpay_success") == "1"
if just_paid:
    # Force a fresh poll so the success banner reflects reality.
    try:
        sub = subscription.poll_and_update(me["id"]) or sub
    except Exception:
        pass


st.title("Account")

if just_paid:
    st.success(
        "🎉 **Payment confirmed.** Your subscription is now active — "
        "thanks for upgrading."
    )

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
        st.warning(f"⏰ **Trial ends in {hours_left} hours.** Subscribe below to keep your campaigns running.")
    else:
        st.info(f"Free trial · {days_left} day(s) remaining")
elif status == "active":
    end = db.parse_iso(sub.get("current_period_end"))
    end_str = end.strftime("%d %b %Y") if end else "—"
    st.success(f"✅ Active · renews {end_str}")
elif status == "past_due":
    st.error("⚠️ Payment failed. Update your payment method to keep your campaigns running.")
elif status == "expired":
    st.error("Subscription expired. Subscribe below to resume your campaigns.")
elif status == "canceled":
    st.warning("Subscription canceled. Subscribe below to resume.")

st.divider()


# ---------- Upgrade flow ----------
price = PRICING[me["currency"]]
plan_id = subscription.plan_id_for(me["currency"])
is_active = status == "active"

st.subheader("Manage plan" if is_active else "Upgrade your plan")

# Plan card — gradient header + feature list + primary CTA
plan_card = st.container(border=True)
with plan_card:
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1877F2 0%, #4267B2 100%);
            color: white;
            padding: 18px 22px;
            border-radius: 8px;
            margin-bottom: 14px;
        ">
            <div style="font-size: 13px; opacity: 0.85; letter-spacing: 0.3px;">STARTER</div>
            <div style="font-size: 30px; font-weight: 700; line-height: 1.1; margin-top: 2px;">
                {price['currency_symbol']}{price['amount']}
                <span style="font-size: 14px; font-weight: 400; opacity: 0.85;">/ month</span>
            </div>
            <div style="font-size: 13px; opacity: 0.85; margin-top: 6px;">
                Billed monthly · cancel anytime
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown(
            "- ✅ 1 client Meta ad account\n"
            "- ✅ Facebook + Instagram placements\n"
            "- ✅ AI ad copy (Gemini)\n"
            "- ✅ Auto-pause / auto-resume"
        )
    with fc2:
        st.markdown(
            "- ✅ Live KPI dashboard\n"
            "- ✅ One-click campaign launch\n"
            "- ✅ Instant Form lead ads\n"
            "- ✅ Email + WhatsApp support"
        )
    st.markdown("")  # spacer

    if not (subscription.razorpay_configured() and plan_id):
        st.error(
            "Subscription billing is temporarily unavailable. "
            f"Please email **sukumarpoddar90@gmail.com** to subscribe."
        )
    elif is_active:
        st.caption(
            "You're on Starter. To change card, cancel, or manage invoices, "
            "use the Razorpay link in your last billing email — or message "
            f"**WhatsApp {WHATSAPP_NUMBER}**."
        )
    else:
        cta_label = (
            f"Subscribe — {price['currency_symbol']}{price['amount']}/month"
            if status in ("expired", "canceled", "past_due")
            else f"Continue to Razorpay · {price['currency_symbol']}{price['amount']}/month"
        )
        if st.button(cta_label, type="primary", use_container_width=True, key="rzp_subscribe"):
            try:
                with st.spinner("Setting up your subscription…"):
                    result = subscription.create_subscription(
                        user={"id": me["id"], "email": me["email"], "tier": me["tier"]},
                        plan_id=plan_id,
                    )
                checkout_url = result.get("short_url")
                if checkout_url:
                    # Stash the URL — Streamlit re-renders after the click,
                    # we want the redirect HTML to survive.
                    st.session_state["_rzp_checkout_url"] = checkout_url
                    st.rerun()
                else:
                    st.error("Could not generate a Razorpay checkout link. Please retry.")
            except Exception as e:
                st.error(f"Razorpay error: {e}")

        # Surface the redirect target after rerun
        checkout_url = st.session_state.pop("_rzp_checkout_url", None)
        if checkout_url:
            st.success("Opening secure Razorpay checkout…")
            st.markdown(
                f'<meta http-equiv="refresh" content="0; url={checkout_url}">',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<a href="{checkout_url}" target="_self" '
                'style="display:inline-block;padding:10px 18px;background:#1877F2;'
                'color:white;border-radius:6px;text-decoration:none;font-weight:600;">'
                "Click here if not redirected →</a>",
                unsafe_allow_html=True,
            )

        st.caption(
            "🔒 Payments are processed securely by Razorpay. "
            "Card details never touch our servers."
        )

        st.markdown("")
        rc1, rc2 = st.columns([2, 1])
        rc1.caption("Already completed payment? Sync your subscription status from Razorpay.")
        if rc2.button("Refresh status", use_container_width=True, key="rzp_refresh"):
            try:
                with st.spinner("Checking Razorpay…"):
                    subscription.poll_and_update(me["id"])
                st.rerun()
            except Exception as e:
                st.error(f"Could not refresh: {e}")

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
