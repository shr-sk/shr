"""Subscription provider abstraction — Razorpay primary, manual fallback.

When `RAZORPAY_KEY_ID` is not set in env (early pilot), the system falls back
to a manual-payment flow: user clicks Upgrade → sees UPI / bank details
and a WhatsApp link → admin manually marks them paid in /admin → subscription
extends 30 days.

When `RAZORPAY_KEY_ID` IS set, the same Upgrade button creates a Razorpay
Subscription and redirects to hosted Razorpay Checkout.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from . import db

if TYPE_CHECKING:
    pass


# ---------- Pricing ----------

PRICING = {
    "INR": {"amount": 999, "currency_symbol": "₹"},
    "USD": {"amount": 21,  "currency_symbol": "$"},
}


WHATSAPP_NUMBER = "+91 9102916841"
SUPPORT_EMAIL = "support@your-domain.com"   # update once you have one


# ---------- Provider detection ----------

def razorpay_configured() -> bool:
    return bool(
        os.environ.get("RAZORPAY_KEY_ID")
        and os.environ.get("RAZORPAY_KEY_SECRET")
    )


def plan_id_for(currency: str) -> str | None:
    if currency == "INR":
        return os.environ.get("RAZORPAY_PLAN_ID_INR")
    if currency == "USD":
        return os.environ.get("RAZORPAY_PLAN_ID_USD")
    return None


# ---------- Razorpay calls (lazy import) ----------

def _client():
    """Lazy import + init the Razorpay client. Raises if not configured."""
    if not razorpay_configured():
        raise RuntimeError("Razorpay not configured")
    import razorpay  # type: ignore[import-not-found]
    return razorpay.Client(auth=(
        os.environ["RAZORPAY_KEY_ID"],
        os.environ["RAZORPAY_KEY_SECRET"],
    ))


def create_subscription(user: dict, plan_id: str) -> dict:
    """Create a Razorpay Subscription. Returns {subscription_id, short_url}.

    `short_url` is the hosted-checkout URL we send the user to.
    """
    client = _client()
    sub = client.subscription.create({
        "plan_id": plan_id,
        "customer_notify": 1,
        "total_count": 12,           # 12 months = renew monthly for 12 cycles
        "notes": {
            "email": user["email"],
            "user_id": str(user["id"]),
            "tier": user["tier"],
        },
    })
    db.set_razorpay_ids(
        user_id=user["id"],
        subscription_id=sub.get("id"),
        customer_id=sub.get("customer_id"),
    )
    return {
        "subscription_id": sub.get("id"),
        "short_url": sub.get("short_url"),
    }


def fetch_subscription(subscription_id: str) -> dict:
    """Poll Razorpay for the latest status of a subscription."""
    client = _client()
    return client.subscription.fetch(subscription_id)


def poll_and_update(user_id: int) -> dict | None:
    """Read Razorpay's view of the user's subscription and sync our DB.

    Called lazily — on every page load — so the DB reflects reality without
    needing a webhook for v1.
    """
    sub_row = db.get_subscription(user_id)
    if not sub_row or not sub_row.get("razorpay_subscription_id"):
        return sub_row

    if not razorpay_configured():
        return sub_row

    try:
        remote = fetch_subscription(sub_row["razorpay_subscription_id"])
    except Exception:
        return sub_row   # transient — keep current state

    # Map Razorpay status -> our status
    remote_status = remote.get("status", "")
    mapped = {
        "active":    "active",
        "authenticated": "active",
        "pending":   "trialing",
        "halted":    "past_due",
        "cancelled": "canceled",
        "completed": "canceled",
        "expired":   "expired",
    }.get(remote_status, sub_row["status"])

    period_end = None
    if remote.get("current_end"):
        from datetime import datetime, timezone
        period_end = datetime.fromtimestamp(remote["current_end"], tz=timezone.utc).isoformat()

    db.set_subscription_status(user_id, mapped, period_end)
    return db.get_subscription(user_id)
