"""Take a validated MetaCampaignYaml and produce the operation list.

Meta Marketing API call order is strict:
  1. Campaign  POST /act_{acct}/campaigns                  -> id
  2. Ad Set    POST /act_{acct}/adsets   (uses campaign_id) -> id
  3. Ad        POST /act_{acct}/ads      (uses adset_id + inline creative)
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from schemas import MetaCampaignYaml


CAMPAIGN_REF = "${CAMPAIGN_ID}"
AD_SET_REF = "${AD_SET_ID}"


def _strip_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _build_asset_feed_spec(ld, cta_value: dict) -> dict:
    """Build Meta's `asset_feed_spec` with placement-specific image rules.

    Image-to-placement mapping (each placement gets its best-fit image):

      • image_hash         (1:1, ~1080x1080) -> FB Feed + IG Feed (default)
      • image_hash_story   (9:16, ~1080x1920) -> FB Stories + IG Stories + Reels
      • image_hash_portrait (4:5, ~1080x1350) -> IG Feed (better engagement)

    Customization rules are evaluated by Meta in order; the FIRST matching
    rule wins. So put more-specific (IG portrait) BEFORE the generic feed rule.
    """
    images: list[dict] = [{"hash": ld.image_hash}]
    rules: list[dict] = []

    if ld.image_hash_story:
        images.append({"hash": ld.image_hash_story})
        rules.append({
            "customization_spec": {
                "publisher_platforms": ["facebook", "instagram"],
                "facebook_positions": ["story"],
                "instagram_positions": ["story", "reels"],
            },
            "image_label": {"hash": ld.image_hash_story},
        })

    if ld.image_hash_portrait:
        images.append({"hash": ld.image_hash_portrait})
        # IG Feed only — must come BEFORE the generic 1:1 rule
        rules.append({
            "customization_spec": {
                "publisher_platforms": ["instagram"],
                "instagram_positions": ["stream"],
            },
            "image_label": {"hash": ld.image_hash_portrait},
        })

    # Generic 1:1 fallback rule (covers FB Feed + IG Feed when not overridden)
    rules.append({
        "customization_spec": {
            "publisher_platforms": ["facebook", "instagram"],
            "facebook_positions": ["feed"],
            "instagram_positions": ["stream"],
        },
        "image_label": {"hash": ld.image_hash},
    })

    spec_out: dict = {
        "images": images,
        "bodies": [{"text": ld.message}],
        "titles": [{"text": ld.name}],
        "link_urls": [{"website_url": ld.link}],
        "ad_formats": ["SINGLE_IMAGE"],
        "call_to_action_types": [ld.call_to_action.type],
        "asset_customization_rules": rules,
    }
    if ld.description:
        spec_out["descriptions"] = [{"text": ld.description}]
    # Lead-form case: pass form_id alongside CTA via cta_value
    if cta_value.get("lead_gen_form_id"):
        spec_out["additional_data"] = {
            "lead_gen_form_id": cta_value["lead_gen_form_id"]
        }
    return spec_out


def build_campaign(spec: MetaCampaignYaml) -> dict:
    c = spec.campaign
    payload: dict[str, Any] = {
        "name": c.name,
        "objective": c.objective,
        # Status driven by the YAML — default 'PAUSED' in the schema. The
        # dashboard exposes a "Launch as PAUSED / ACTIVE" radio.
        "status": c.status,
        "special_ad_categories": c.special_ad_categories,
        "buying_type": c.buying_type,
        # Required by newer Marketing API versions when CBO is not enabled.
        # We're putting the budget on the ad_set, so explicitly say False.
        "is_adset_budget_sharing_enabled": False,
    }
    if c.special_ad_category_country:
        payload["special_ad_category_country"] = c.special_ad_category_country
    if c.spend_cap is not None:
        payload["spend_cap"] = c.spend_cap
    if c.daily_budget is not None:
        payload["daily_budget"] = c.daily_budget
    if c.lifetime_budget is not None:
        payload["lifetime_budget"] = c.lifetime_budget
    return {
        "resource_type": "campaign",
        "ref_key": "campaign",
        "endpoint": f"act_{spec.ad_account_id}/campaigns",
        "payload": payload,
    }


def build_ad_set(spec: MetaCampaignYaml) -> dict:
    s = spec.ad_set

    geo = _strip_none({
        "countries": s.targeting.geo_locations.countries or None,
        "cities": s.targeting.geo_locations.cities or None,
        "regions": s.targeting.geo_locations.regions or None,
        "custom_locations": [cl.model_dump() for cl in s.targeting.geo_locations.custom_locations] or None,
        "location_types": s.targeting.geo_locations.location_types,
    })

    flexible_spec_payload = [
        _strip_none({
            "interests": [i.model_dump(exclude_none=True) for i in b.interests] or None,
            "behaviors": [bh.model_dump(exclude_none=True) for bh in b.behaviors] or None,
        })
        for b in s.targeting.flexible_spec
    ] or None

    targeting_payload = _strip_none({
        "geo_locations": geo,
        "age_min": s.targeting.age_min,
        "age_max": s.targeting.age_max,
        "genders": s.targeting.genders or None,
        "locales": s.targeting.locales or None,
        "flexible_spec": flexible_spec_payload,
        "publisher_platforms": s.targeting.publisher_platforms,
        "facebook_positions": s.targeting.facebook_positions,
        "instagram_positions": s.targeting.instagram_positions,
        # Required by Meta since 2024 — explicit Advantage Audience on/off.
        "targeting_automation": s.targeting.targeting_automation.model_dump(),
    })

    payload: dict[str, Any] = {
        "name": s.name,
        "campaign_id": CAMPAIGN_REF,
        # Ad set inherits the launch status set on the campaign (so the whole
        # tree comes up together — no point launching the ad set ACTIVE if the
        # campaign above it is PAUSED).
        "status": spec.campaign.status,
        "optimization_goal": s.optimization_goal,
        "billing_event": s.billing_event,
        "bid_strategy": s.bid_strategy,
        "destination_type": s.destination_type,
        "targeting": targeting_payload,
    }
    if s.bid_amount is not None:
        payload["bid_amount"] = s.bid_amount
    if s.daily_budget is not None:
        payload["daily_budget"] = s.daily_budget
    if s.lifetime_budget is not None:
        payload["lifetime_budget"] = s.lifetime_budget
    if s.start_time:
        payload["start_time"] = s.start_time.isoformat()
    if s.end_time:
        payload["end_time"] = s.end_time.isoformat()
    if s.promoted_object:
        payload["promoted_object"] = s.promoted_object.model_dump(exclude_none=True)
    if s.dsa_payor:
        payload["dsa_payor"] = s.dsa_payor
    if s.dsa_beneficiary:
        payload["dsa_beneficiary"] = s.dsa_beneficiary

    return {
        "resource_type": "ad_set",
        "ref_key": "ad_set",
        "endpoint": f"act_{spec.ad_account_id}/adsets",
        "payload": payload,
    }


def build_ad(spec: MetaCampaignYaml) -> dict:
    a = spec.ad
    ld = a.creative.object_story_spec.link_data
    # CTA `value` shape depends on destination:
    #   • Website ads   -> {"link": "https://..."}
    #   • Lead-form ads -> {"lead_gen_form_id": "<form_id>"}
    cta_value: dict[str, str] = {}
    if ld.call_to_action.value_lead_gen_form_id:
        cta_value["lead_gen_form_id"] = ld.call_to_action.value_lead_gen_form_id
    else:
        cta_value["link"] = ld.call_to_action.value_link or ld.link

    has_extras = bool(ld.image_hash_story or ld.image_hash_portrait)

    object_story_spec_payload = _strip_none({
        "page_id": a.creative.object_story_spec.page_id,
        "instagram_actor_id": a.creative.object_story_spec.instagram_actor_id,
        # link_data is needed when there is only ONE image. With asset_feed_spec
        # we still keep page_id/IG actor here but skip the link_data block.
        "link_data": None if has_extras else _strip_none({
            "image_hash": ld.image_hash,
            "message": ld.message,
            "name": ld.name,
            "description": ld.description,
            "link": ld.link,
            "call_to_action": {"type": ld.call_to_action.type, "value": cta_value},
        }),
    })

    creative_payload: dict = _strip_none({
        "name": a.creative.name,
        "object_story_spec": object_story_spec_payload,
        "url_tags": a.creative.url_tags,
    })

    if has_extras:
        creative_payload["asset_feed_spec"] = _build_asset_feed_spec(ld, cta_value)

    return {
        "resource_type": "ad",
        "ref_key": "ad",
        "endpoint": f"act_{spec.ad_account_id}/ads",
        "payload": {
            "name": a.name,
            "adset_id": AD_SET_REF,
            # Inherits the campaign-level status (PAUSED or ACTIVE).
            "status": spec.campaign.status,
            "creative": creative_payload,
        },
    }


def build_all(spec: MetaCampaignYaml) -> list[dict]:
    return [build_campaign(spec), build_ad_set(spec), build_ad(spec)]
