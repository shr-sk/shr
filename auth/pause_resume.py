"""Auto-pause / auto-resume Meta campaigns on billing events.

When a user's subscription lapses (trial expires without payment, payment
fails, subscription cancelled), we call Meta's API to PAUSE all their active
campaigns. The list of paused campaign IDs is stored in our DB. When the
subscription is reactivated, we read that list and RESUME each one.

This protects the user — their ad spend doesn't keep running for a service
they're no longer paying for — and gives us hard payment enforcement.
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import db

# Reuse the live_fetcher functions for pause/resume calls
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _safe_import():
    """Lazy import — avoids requiring requests/META token at import time."""
    from live_fetcher import (  # type: ignore[import-not-found]
        fetch_campaigns,
        pause_campaign,
        resume_campaign,
    )
    return fetch_campaigns, pause_campaign, resume_campaign


def pause_user_campaigns(user_id: int) -> dict:
    """Pause all ACTIVE campaigns belonging to this user's clients.

    Records the paused campaign_ids in subscriptions.paused_campaign_ids so
    they can be auto-resumed later.

    Returns: {"paused": [...], "skipped": [...], "errors": [...]}
    """
    result = {"paused": [], "skipped": [], "errors": []}
    try:
        fetch_campaigns, pause_campaign, _ = _safe_import()
    except Exception as e:
        result["errors"].append(f"Meta API import failed: {e}")
        return result

    clients = db.list_clients(user_id)
    for client in clients:
        try:
            rows = fetch_campaigns(client["ad_account_id"], lookback="last_30d")
        except Exception as e:
            result["errors"].append(f"fetch failed for {client['ad_account_id']}: {e}")
            continue

        for row in rows:
            if row.status != "ACTIVE":
                result["skipped"].append(row.campaign_id)
                continue
            try:
                pause_campaign(row.campaign_id)
                result["paused"].append(row.campaign_id)
            except Exception as e:
                result["errors"].append(f"pause failed for {row.campaign_id}: {e}")

    # Persist the paused list so we can resume them later
    db.set_paused_campaigns(user_id, result["paused"])
    return result


def resume_user_campaigns(user_id: int) -> dict:
    """Resume campaigns that were paused due to billing.

    Only touches campaigns we paused — won't accidentally re-enable a campaign
    the user paused manually.

    Returns: {"resumed": [...], "errors": [...]}
    """
    result = {"resumed": [], "errors": []}
    try:
        _, _, resume_campaign = _safe_import()
    except Exception as e:
        result["errors"].append(f"Meta API import failed: {e}")
        return result

    sub = db.get_subscription(user_id)
    paused_ids = (sub or {}).get("paused_campaign_ids") or []
    for campaign_id in paused_ids:
        try:
            resume_campaign(campaign_id)
            result["resumed"].append(campaign_id)
        except Exception as e:
            result["errors"].append(f"resume failed for {campaign_id}: {e}")

    # Clear the list now that we've tried to resume everything
    db.set_paused_campaigns(user_id, [])
    return result
