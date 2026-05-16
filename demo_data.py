"""Hardcoded demo data for the Dashboard + Manage views.

Two scenarios — one per currency — so the toggle on the sidebar swaps which
fake campaign shows up.

Drop this file when going live; nothing imports it from the production path.
"""
from __future__ import annotations

from live_fetcher import CampaignRow


DEMO_CONFIG = {
    "USD": {
        "ad_account_id": "204512345678901",
        "campaign_id":   "23851234567890123",
        "campaign_name": "Brooklyn Reads — Spring Roast — Conversions",
        "destination":   "Website",
        "objective":     "OUTCOME_TRAFFIC",
        "stats": {
            "impressions":           8_234,
            "reach":                 5_120,
            "clicks":                412,
            "spend":                 218.40,        # USD
            "ctr":                   0.0500,
            "avg_cpc":               0.53,
            "conversions":           18.0,
            "conversion_value":      684.00,
        },
    },
    "INR": {
        "ad_account_id": "204512345678902",
        "campaign_id":   "23851234567890456",
        "campaign_name": "Kapoor & Associates — ITR Filing FY25-26 — Leads",
        "destination":   "Lead Form",
        "objective":     "OUTCOME_LEADS",
        "stats": {
            "impressions":           24_580,
            "reach":                 14_750,
            "clicks":                612,
            "spend":                 14_280.00,     # INR
            "ctr":                   0.0249,
            "avg_cpc":               23.33,
            "conversions":           47.0,          # leads
            "conversion_value":      0.0,           # no revenue tracking for leads
        },
    },
}


def demo_rows(currency: str = "USD", status: str = "ACTIVE") -> list[CampaignRow]:
    """One-row list shaped exactly like live_fetcher.fetch_campaigns()."""
    cfg = DEMO_CONFIG.get(currency, DEMO_CONFIG["USD"])
    s = cfg["stats"]
    return [
        CampaignRow(
            campaign_id=cfg["campaign_id"],
            name=cfg["campaign_name"],
            status=status,  # type: ignore[arg-type]
            objective=cfg["objective"],
            destination=cfg["destination"],
            impressions=int(s["impressions"]),
            reach=int(s["reach"]),
            clicks=int(s["clicks"]),
            spend=float(s["spend"]),
            ctr=float(s["ctr"]),
            avg_cpc=float(s["avg_cpc"]),
            conversions=float(s["conversions"]),
            conversion_value=float(s["conversion_value"]),
        )
    ]


def demo_ad_account_id(currency: str = "USD") -> str:
    return DEMO_CONFIG.get(currency, DEMO_CONFIG["USD"])["ad_account_id"]
