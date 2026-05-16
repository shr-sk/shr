"""Read per-campaign KPIs + mutate campaign status against the Meta Marketing API.

Conversions on Meta come from one of two paths:
  • Lead Form ads — Meta tracks `leads` server-side, no setup required.
  • Website ads — `actions[purchase]` populated via Pixel + CAPI on the
    client's site. Without Pixel, conversion fields stay zero.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


CampaignStatus = Literal["ACTIVE", "PAUSED", "DELETED", "ARCHIVED", "UNKNOWN"]


@dataclass
class CampaignRow:
    campaign_id: str
    name: str
    status: CampaignStatus
    objective: str
    destination: str          # "Website" or "Lead Form"
    impressions: int
    reach: int
    clicks: int
    spend: float              # in account currency (not minor units)
    ctr: float                # 0.0–1.0
    avg_cpc: float
    conversions: float
    conversion_value: float

    @property
    def cac(self) -> float | None:
        return self.spend / self.conversions if self.conversions else None

    @property
    def roas(self) -> float | None:
        return self.conversion_value / self.spend if self.spend else None

    @property
    def conversion_rate(self) -> float | None:
        return self.conversions / self.clicks if self.clicks else None


def _load_env_once():
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    env_path = Path(__file__).parent / "payload_pipeline" / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def fetch_campaigns(
    ad_account_id: str,
    *,
    lookback: str = "last_30d",
) -> list[CampaignRow]:
    """Hit Meta Marketing API for per-campaign insights.

    Returns one CampaignRow per (campaign × non-empty insights). Campaigns
    with zero impressions in the window are still returned (zeros).

    `lookback` accepts Meta's date_preset enum:
      today, yesterday, last_3d, last_7d, last_14d, last_28d, last_30d,
      last_90d, this_month, last_month, this_quarter, lifetime.
    """
    _load_env_once()
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "META_ACCESS_TOKEN not set. Add it to Meta_Ads/payload_pipeline/.env"
        )

    try:
        import requests  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("`requests` not installed. pip install requests") from e

    # Two-call shape: campaigns list → insights per campaign (Meta's design).
    api_ver = "v20.0"
    base = f"https://graph.facebook.com/{api_ver}/act_{ad_account_id}"

    campaigns_resp = requests.get(
        f"{base}/campaigns",
        params={
            "fields": "id,name,status,objective,destination_type",
            "access_token": token,
            "limit": 200,
        },
        timeout=30,
    )
    campaigns_resp.raise_for_status()
    campaigns = campaigns_resp.json().get("data", [])

    rows: list[CampaignRow] = []
    for c in campaigns:
        ins_resp = requests.get(
            f"https://graph.facebook.com/{api_ver}/{c['id']}/insights",
            params={
                "fields": "impressions,reach,clicks,spend,ctr,cpc,actions,action_values",
                "date_preset": lookback,
                "access_token": token,
            },
            timeout=30,
        )
        ins_resp.raise_for_status()
        data = ins_resp.json().get("data", [])
        ins = data[0] if data else {}

        # Conversion logic:
        #   • For Lead Form ads (destination_type=ON_AD), look for actions[lead].
        #   • For Website ads, look for actions[offsite_conversion.fb_pixel_purchase]
        #     or actions[purchase].
        conversions = 0.0
        conversion_value = 0.0
        destination_type = (c.get("destination_type") or "").upper()
        destination = "Lead Form" if destination_type == "ON_AD" else "Website"

        for a in ins.get("actions", []) or []:
            t = a.get("action_type", "")
            if destination == "Lead Form" and t == "lead":
                conversions += float(a.get("value", 0))
            elif destination == "Website" and t in (
                "offsite_conversion.fb_pixel_purchase",
                "purchase",
            ):
                conversions += float(a.get("value", 0))

        for v in ins.get("action_values", []) or []:
            t = v.get("action_type", "")
            if destination == "Website" and t in (
                "offsite_conversion.fb_pixel_purchase",
                "purchase",
            ):
                conversion_value += float(v.get("value", 0))

        rows.append(
            CampaignRow(
                campaign_id=str(c["id"]),
                name=c.get("name", "—"),
                status=_status_to_str(c.get("status", "")),
                objective=c.get("objective", ""),
                destination=destination,
                impressions=int(float(ins.get("impressions", 0))),
                reach=int(float(ins.get("reach", 0))),
                clicks=int(float(ins.get("clicks", 0))),
                spend=float(ins.get("spend", 0)),
                ctr=float(ins.get("ctr", 0)) / 100.0,   # Meta returns CTR as percentage
                avg_cpc=float(ins.get("cpc", 0)),
                conversions=conversions,
                conversion_value=conversion_value,
            )
        )
    return rows


def _status_to_str(s: str) -> CampaignStatus:
    s = (s or "").upper()
    if s in ("ACTIVE", "PAUSED", "DELETED", "ARCHIVED"):
        return s  # type: ignore[return-value]
    return "UNKNOWN"


def fetch_account_totals(rows: list[CampaignRow]) -> dict:
    """Aggregate per-campaign rows into one account-level KPI dict."""
    total_spend = sum(r.spend for r in rows)
    total_clicks = sum(r.clicks for r in rows)
    total_imps = sum(r.impressions for r in rows)
    total_reach = sum(r.reach for r in rows)
    total_conv = sum(r.conversions for r in rows)
    total_value = sum(r.conversion_value for r in rows)
    return {
        "spend":             total_spend,
        "clicks":            total_clicks,
        "impressions":       total_imps,
        "reach":             total_reach,
        "ctr":               (total_clicks / total_imps) if total_imps else 0.0,
        "avg_cpc":           (total_spend / total_clicks) if total_clicks else 0.0,
        "conversions":       total_conv,
        "conversion_value":  total_value,
        "cac":               (total_spend / total_conv) if total_conv else None,
        "roas":              (total_value / total_spend) if total_spend else None,
        "conversion_rate":   (total_conv / total_clicks) if total_clicks else None,
        "campaign_count":    len(rows),
        "active_count":      sum(1 for r in rows if r.status == "ACTIVE"),
    }


# ---------- Mutations ----------

def _mutate_status(campaign_id: str, new_status: str) -> dict:
    _load_env_once()
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("META_ACCESS_TOKEN not set.")
    try:
        import requests  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("`requests` not installed.") from e

    resp = requests.post(
        f"https://graph.facebook.com/v20.0/{campaign_id}",
        params={"access_token": token},
        data={"status": new_status},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def pause_campaign(campaign_id: str) -> dict:
    return _mutate_status(campaign_id, "PAUSED")


def resume_campaign(campaign_id: str) -> dict:
    return _mutate_status(campaign_id, "ACTIVE")


def stop_campaign(campaign_id: str) -> dict:
    """DELETED is permanent — UI must confirm before calling."""
    return _mutate_status(campaign_id, "DELETED")
