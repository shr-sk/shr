"""Page gate — call at top of every protected view.

Three terminal states:
  • Not logged in        → redirect to login page (st.stop)
  • Trial / sub expired  → redirect to account page with upgrade CTA (st.stop)
  • Active / trialing    → page renders normally
"""
from __future__ import annotations

import streamlit as st

from . import auth, db, pause_resume, subscription
from datetime import datetime, timezone


def _login_link():
    # Page-aware "go to" — Streamlit's `st.switch_page` only accepts paths
    # relative to the entry-point dir. We use it where possible; otherwise
    # we stop with a clear message.
    try:
        st.switch_page("views/login.py")
    except Exception:
        st.warning("Please sign in to continue.")
        st.stop()


def _account_link():
    try:
        st.switch_page("views/account.py")
    except Exception:
        st.warning("Your subscription needs attention.")
        st.stop()


def _check_trial_expiry(user: dict) -> str:
    """If trial has passed without a paid sub, flip status to 'expired'
    and pause the user's campaigns. Returns the new status."""
    sub = db.get_subscription(user["id"]) or {}
    if sub.get("status") != "trialing":
        return sub.get("status", "expired")

    trial_end = db.parse_iso(user.get("trial_ends_at"))
    if trial_end and datetime.now(timezone.utc) > trial_end:
        # Trial passed without payment — expire + pause active campaigns
        db.set_subscription_status(user["id"], "expired")
        # Best-effort pause (won't crash gate if Meta API unreachable)
        try:
            pause_resume.pause_user_campaigns(user["id"])
        except Exception:
            pass
        return "expired"
    return "trialing"


def gate(*, require_admin: bool = False) -> dict:
    """Enforce auth + active subscription. Returns the current user dict.

    Stops execution unless the user is logged in AND has an active or
    trialing subscription. Admin pages may set require_admin=True.
    """
    me = auth.current_user()
    if not me:
        _login_link()
        st.stop()  # safety

    if require_admin and not me["is_admin"]:
        st.error("Admin access required.")
        st.stop()

    user_row = db.find_user(me["id"])
    if not user_row:
        auth.clear_session()
        _login_link()
        st.stop()

    # 1. Trial expiry check (lazy)
    status = _check_trial_expiry(user_row)

    # 2. If Razorpay-managed, poll for fresh remote status
    sub = db.get_subscription(me["id"]) or {}
    if subscription.razorpay_configured() and sub.get("razorpay_subscription_id"):
        try:
            sub = subscription.poll_and_update(me["id"]) or sub
        except Exception:
            pass
        status = sub.get("status", status)

    # 3. Auto-resume if a previously-expired user has just paid + we have
    #    campaigns sitting in paused_campaign_ids waiting to come back
    if status == "active" and sub.get("paused_campaign_ids"):
        try:
            pause_resume.resume_user_campaigns(me["id"])
        except Exception:
            pass

    # 4. Final gate decision
    if status in ("expired", "canceled", "past_due"):
        st.error(
            f"Your subscription is **{status}**. Renew to continue."
        )
        st.markdown("Go to **Account** → Upgrade.")
        _account_link()
        st.stop()

    return dict(me)
