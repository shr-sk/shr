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
from styles import hero, inject_css, section_label, status_pill

inject_css()


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
    try:
        sub = subscription.poll_and_update(me["id"]) or sub
    except Exception:
        pass


hero(
    "Account",
    kicker="Subscription & profile",
    subtitle="Manage your plan, see your billing status, and sign out.",
)

if just_paid:
    st.success(
        "Payment confirmed. Your subscription is now active — thanks for upgrading."
    )

# ---------- Profile summary ----------
profile = st.container(border=True)
with profile:
    section_label("Your profile")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Email** — {me['email']}")
        st.markdown(f"**Currency** — {me['currency']}")
        st.markdown(f"**Tier** — `{me['tier']}`")
    with c2:
        st.markdown(f"**Client limit** — {me['client_limit']}")
        st.markdown(f"**Team seats** — {me['team_seats']}")
        st.markdown(f"**Member since** — {user_row['created_at'][:10] if user_row else '—'}")


# ---------- Subscription status ----------
status = sub.get("status", "expired")
trial_end = db.parse_iso(user_row.get("trial_ends_at")) if user_row else None
now = datetime.now(timezone.utc)

status_card = st.container(border=True)
with status_card:
    section_label("Subscription status")
    pill = status_pill(status)
    if status == "trialing":
        days_left = (trial_end - now).days if trial_end else 0
        hours_left = max(0, int((trial_end - now).total_seconds() / 3600)) if trial_end else 0
        message = (
            f"Trial ends in {hours_left} hours — subscribe below to keep going."
            if hours_left < 24
            else f"Free trial · {days_left} day(s) remaining."
        )
    elif status == "active":
        end = db.parse_iso(sub.get("current_period_end"))
        end_str = end.strftime("%d %b %Y") if end else "—"
        message = f"Renews on {end_str}."
    elif status == "past_due":
        message = "Payment failed. Update your payment method to keep campaigns running."
    elif status == "expired":
        message = "Subscription expired. Subscribe below to resume your campaigns."
    elif status == "canceled":
        message = "Subscription canceled. Subscribe below to resume."
    else:
        message = "—"

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:12px;margin-top:4px;'>"
        f"{pill}"
        f"<span style='color:#54595F;font-size:14px;'>{message}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------- Upgrade flow ----------
price = PRICING[me["currency"]]
plan_id = subscription.plan_id_for(me["currency"])
is_active = status == "active"

st.markdown("")  # spacer

plan_card = st.container(border=True)
with plan_card:
    section_label("Manage plan" if is_active else "Upgrade your plan")
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1877F2 0%, #3856A8 100%);
            color: white;
            padding: 20px 24px;
            border-radius: 10px;
            margin: 4px 0 14px 0;
            box-shadow: 0 1px 2px rgba(56,86,168,0.18), 0 8px 24px rgba(56,86,168,0.12);
        ">
            <div style="font-size:11px;letter-spacing:.18em;text-transform:uppercase;opacity:.85;">STARTER</div>
            <div style="font-size:30px;font-weight:700;line-height:1.1;margin-top:4px;">
                {price['currency_symbol']}{price['amount']}
                <span style="font-size:14px;font-weight:400;opacity:.85;"> / month</span>
            </div>
            <div style="font-size:13px;opacity:.85;margin-top:6px;">
                Billed monthly · cancel anytime
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown(
            "- 1 client Meta ad account\n"
            "- Facebook + Instagram placements\n"
            "- AI ad copy (Gemini)\n"
            "- Auto-pause / auto-resume"
        )
    with fc2:
        st.markdown(
            "- Live KPI dashboard\n"
            "- One-click campaign launch\n"
            "- Instant Form lead ads\n"
            "- Email + WhatsApp support"
        )
    st.markdown("")

    if not (subscription.razorpay_configured() and plan_id):
        st.error(
            "Subscription billing is temporarily unavailable. "
            "Please email sukumarpoddar90@gmail.com to subscribe."
        )
    elif is_active:
        st.caption(
            "You're on Starter. To change card, cancel, or download invoices, "
            "open the link in your most recent Razorpay billing email — or "
            f"message WhatsApp {WHATSAPP_NUMBER}."
        )
    else:
        # If we just generated a checkout URL on a previous click, show the
        # "open in new tab" button rather than re-creating the subscription.
        pending_url = st.session_state.get("_rzp_checkout_url")

        if pending_url:
            # Open in a NEW TAB so the original Account tab stays mounted.
            # When the user pays and closes the Razorpay tab, they're already
            # back on Account — no jarring navigation needed.
            st.success(
                "Your secure Razorpay checkout is ready. Open it in a new tab, "
                "complete payment, then click **Refresh status** below."
            )
            st.markdown(
                f'<a href="{pending_url}" target="_blank" rel="noopener noreferrer" '
                'style="display:inline-block;width:100%;text-align:center;'
                'padding:12px 18px;background:linear-gradient(135deg,#1877F2 0%,#3856A8 100%);'
                'color:white;border-radius:8px;text-decoration:none;font-weight:600;'
                'font-size:15px;letter-spacing:.01em;'
                'box-shadow:0 1px 2px rgba(24,119,242,0.18), 0 4px 14px rgba(24,119,242,0.12);">'
                "Open Razorpay checkout →"
                "</a>",
                unsafe_allow_html=True,
            )
            st.markdown("")
            if st.button("Cancel — generate a new link", use_container_width=False, key="rzp_cancel"):
                st.session_state.pop("_rzp_checkout_url", None)
                st.rerun()

        else:
            cta_label = (
                f"Subscribe — {price['currency_symbol']}{price['amount']}/month"
                if status in ("expired", "canceled", "past_due")
                else f"Continue to Razorpay — {price['currency_symbol']}{price['amount']}/month"
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
                        st.session_state["_rzp_checkout_url"] = checkout_url
                        st.rerun()
                    else:
                        st.error("Could not generate a Razorpay checkout link. Please retry.")
                except Exception as e:
                    st.error(f"Razorpay error: {e}")

        st.caption(
            "Payments are processed securely by Razorpay. "
            "Card details never touch our servers."
        )

        st.markdown("")
        rc1, rc2 = st.columns([2, 1])
        rc1.caption("Already completed payment? Sync your subscription status from Razorpay.")
        if rc2.button("Refresh status", use_container_width=True, key="rzp_refresh"):
            try:
                with st.spinner("Checking Razorpay…"):
                    fresh = subscription.poll_and_update(me["id"])
                # Clear stored checkout URL on confirmed activation.
                if fresh and fresh.get("status") == "active":
                    st.session_state.pop("_rzp_checkout_url", None)
                st.rerun()
            except Exception as e:
                st.error(f"Could not refresh: {e}")


# ---------- Agency tier ----------
st.markdown("")
agency_card = st.container(border=True)
with agency_card:
    section_label("Need more than 1 client?")
    st.markdown(
        """
        | Plan | Clients | Seats | Monthly |
        |---|---|---|---|
        | Agency Lite | 5 | 1 | ₹3,499 / $75 |
        | Agency Standard | 10 | 2 | ₹6,499 / $140 |
        | Agency Pro | 25 | 5 | ₹14,999 / $325 |
        """
    )
    st.caption(
        f"Message WhatsApp **{WHATSAPP_NUMBER}** with your client count and markets. "
        "We'll send a Razorpay invoice and activate within 24 hours."
    )


# ---------- Logout ----------
st.markdown("")
if st.button("Sign out", use_container_width=False):
    auth_mod.clear_session()
    try:
        st.switch_page("views/login.py")
    except Exception:
        st.rerun()
