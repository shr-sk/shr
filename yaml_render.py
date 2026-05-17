"""Translate dashboard inputs into a launcher-ready Meta YAML dict.

Mirrors Google_Ads/yaml_render.py shape but produces a Meta-side YAML —
ad_account_id, campaign, ad_set, ad (with link_data or asset_feed_spec),
and optional lead_form for Instant Form ads.
"""
from __future__ import annotations

from typing import Any

from presets import (
    COUNTRY_TO_ISO,
    CURRENCY,
    CURRENCY_TO_COUNTRY,
    GENDER_TO_META,
    LANGUAGE_TO_LOCALES,
    to_minor,
)


_LEAD_FORM_ID_PLACEHOLDER = "REPLACE_AFTER_LEAD_FORM_CREATED"


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _link_data_block(
    *,
    image_hash: str | None,
    message: str,
    headline: str,
    description: str | None,
    link_target: str,
    cta_type: str,
    is_lead_form: bool,
    image_hash_story: str | None = None,
    image_hash_portrait: str | None = None,
) -> dict:
    if is_lead_form:
        cta = {"type": cta_type, "value_lead_gen_form_id": _LEAD_FORM_ID_PLACEHOLDER}
    else:
        cta = {"type": cta_type, "value_link": link_target}

    block: dict[str, Any] = {
        "image_hash": image_hash or "REPLACE_WITH_UPLOADED_HASH",
        "message": message,
        "name": _truncate(headline, 40),
        "link": link_target,
        "call_to_action": cta,
    }
    if description:
        block["description"] = _truncate(description, 125)
    if image_hash_story:
        block["image_hash_story"] = image_hash_story
    if image_hash_portrait:
        block["image_hash_portrait"] = image_hash_portrait
    return block


def build_meta_yaml(
    *,
    client: dict,
    currency: str,
    ad_copy: dict,
    epicenters: list[dict],
    daily_budget: float,
    destination: str = "Website",          # "Website" or "Lead Form"
    cta_type: str | None = None,
    landing_page_url: str | None = None,
    lead_form_config: dict | None = None,
    country: str | None = None,
    language: str = "English",
    image_hash: str | None = None,
    image_hash_story: str | None = None,
    image_hash_portrait: str | None = None,
    bid_strategy: str = "LOWEST_COST_WITHOUT_CAP",
    objective: str | None = None,
    special_ad_category: str = "NONE",
    start_date: str | None = None,
    end_date: str | None = None,
    launch_status: str = "PAUSED",
) -> dict:
    """Build the Meta YAML dict consumed by payload_pipeline/builders.build_all."""
    country = country or CURRENCY_TO_COUNTRY[currency]
    country_iso = COUNTRY_TO_ISO.get(country, "US")
    locales = LANGUAGE_TO_LOCALES.get(language, [])

    is_lead_form = (destination or "Website").strip().lower().startswith("lead")
    link_target = landing_page_url or client.get("website_url") or "https://example.com"
    cta_type = cta_type or ad_copy.get("call_to_action") or ("GET_QUOTE" if is_lead_form else "LEARN_MORE")
    final_objective = objective or ("OUTCOME_LEADS" if is_lead_form else "OUTCOME_TRAFFIC")
    age_min = int(ad_copy.get("age_min", 18))
    age_max = int(ad_copy.get("age_max", 65))
    gender_pref = (ad_copy.get("gender") or "any").lower()
    gender_label = {"male": "Male only", "female": "Female only"}.get(gender_pref, "Any")
    genders = GENDER_TO_META.get(gender_label, [])

    # Meta rejects country + custom_locations as "overlapping" (custom circles
    # are inside the country). Use ONE or the other:
    #   • epicenters present → custom_locations only (precise circles)
    #   • no epicenters       → country-wide
    geo_locations: dict[str, Any] = {
        "location_types": ["home", "recent"],
    }
    if epicenters:
        geo_locations["custom_locations"] = [
            {
                "latitude": float(e["lat"]),
                "longitude": float(e["lng"]),
                "radius": float(e["radius_km"]),
                "distance_unit": "kilometer",
            }
            for e in epicenters
        ]
    else:
        geo_locations["countries"] = [country_iso]

    # Interests can arrive in two shapes:
    #   list[str]   — raw names from the LLM, NOT resolved to Meta IDs
    #   list[dict]  — resolved via meta_utils.resolve_interest_ids
    #                 each item has a real Meta interest ID + name
    # Meta rejects placeholder/zero IDs (returns OAuthException 100 "Interests
    # with ID 0 is invalid"), so when we don't have real IDs we drop interests
    # entirely — Meta uses broad targeting which is fine for pilot.
    raw_interests = ad_copy.get("interest_targeting") or []
    resolved_interests = [
        i for i in raw_interests
        if isinstance(i, dict) and str(i.get("id", "")).strip() not in ("", "0", "0000000000000")
    ]
    flexible_spec: list[dict] = []
    if resolved_interests:
        flexible_spec.append({"interests": resolved_interests[:5]})

    daily_budget_minor = to_minor(daily_budget, currency)

    ad_set_block: dict[str, Any] = {
        "name": f"{client['business_name']} — Default — Ad set",
        "optimization_goal": "LEAD_GENERATION" if is_lead_form else "LINK_CLICKS",
        "billing_event": "IMPRESSIONS",
        "bid_strategy": bid_strategy,
        "daily_budget": daily_budget_minor,
        "destination_type": "ON_AD" if is_lead_form else "WEBSITE",
        "targeting": {
            "geo_locations": geo_locations,
            "age_min": age_min,
            "age_max": age_max,
            "genders": genders,
            "locales": locales,
            "flexible_spec": flexible_spec,
            "publisher_platforms": ["facebook", "instagram"],
            # Required by Meta since 2024 — Advantage Audience off (0) keeps
            # delivery strict to the geo/age/interests we set. For wider reach
            # campaigns (national-scale brand), flip to 1 to let Meta's AI
            # expand the audience automatically.
            "targeting_automation": {"advantage_audience": 0},
        },
    }
    # Meta requires a `promoted_object` on the ad set for any optimization
    # that needs a target context. For Lead Form (LEAD_GENERATION optimization)
    # the promoted object is the Page that owns the leads.
    # For Website + pixel-tracked conversion, it would be {pixel_id, custom_event_type}.
    if is_lead_form:
        ad_set_block["promoted_object"] = {"page_id": str(client["page_id"])}
    if start_date:
        ad_set_block["start_time"] = f"{start_date}T00:00:00+0000"
    if end_date:
        ad_set_block["end_time"] = f"{end_date}T23:59:00+0000"

    spend_cap = daily_budget_minor * CURRENCY[currency]["default_spend_cap_multiplier"]

    yaml_dict: dict[str, Any] = {
        "ad_account_id": str(client["ad_account_id"]),
        "campaign": {
            "name": f"{client['business_name']} — {('Leads' if is_lead_form else 'Traffic')}",
            "objective": final_objective,
            "status": launch_status,   # PAUSED (safe default) or ACTIVE (start immediately)
            "special_ad_categories": [special_ad_category],
            "buying_type": "AUCTION",
            "spend_cap": spend_cap,
        },
        "ad_set": ad_set_block,
        "ad": {
            "name": f"{client['business_name']} — single image",
            "creative": {
                "name": f"{client['business_name']} creative",
                "object_story_spec": {
                    "page_id": str(client["page_id"]),
                    **(
                        {"instagram_actor_id": str(client["instagram_actor_id"])}
                        if client.get("instagram_actor_id") else {}
                    ),
                    "link_data": _link_data_block(
                        image_hash=image_hash,
                        message=ad_copy.get("primary_text", ""),
                        headline=ad_copy.get("headline", ""),
                        description=ad_copy.get("description"),
                        link_target=link_target,
                        cta_type=cta_type,
                        is_lead_form=is_lead_form,
                        image_hash_story=image_hash_story,
                        image_hash_portrait=image_hash_portrait,
                    ),
                },
            },
        },
    }

    if is_lead_form and lead_form_config:
        # Meta requires form names to be unique per Page. Earlier failed
        # launches may have already created a form with the same name, so
        # Meta returns "Form Name already exists" on retry. Auto-append a
        # timestamp suffix so every build attempt produces a fresh name.
        # (Strip any prior timestamp first so retries don't accumulate them.)
        import re
        from datetime import datetime
        lf = dict(lead_form_config)
        base = re.sub(
            r"\s+\d{6}-\d{6}\s*$", "",
            str(lf.get("name", "Lead form")),
        ).strip()
        stamp = datetime.now().strftime("%y%m%d-%H%M%S")
        lf["name"] = f"{base} {stamp}"
        yaml_dict["lead_form"] = lf

    return yaml_dict
