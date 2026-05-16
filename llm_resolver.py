"""Silent LLM resolver — city geocoding + ad copy generation.

Mirrors the Google_Ads pattern: the dashboard never says "LLM" / "AI" in any
label; it just shows spinners like "Resolving locations…" while Gemini does
the work in the backend.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


# ---------- Location schema ----------

class CityPick(BaseModel):
    name: str = Field(description="City + state/region, e.g. 'Bangalore, Karnataka'.")
    lat: float = Field(description="Latitude in decimal degrees.")
    lng: float = Field(description="Longitude in decimal degrees.")
    radius_km: float = Field(
        ge=1, le=80,
        description="Targeting radius around the city centre in KILOMETRES.",
    )
    why: str = Field(description="One-sentence rationale.")


class LocationGuess(BaseModel):
    cities: list[CityPick] = Field(min_length=1, max_length=10)
    negative_areas: list[str] = Field(default_factory=list)


# ---------- Ad copy schema ----------

class AdCopy(BaseModel):
    primary_text: str = Field(
        max_length=500,
        description="Body of the ad — 2 to 3 short sentences, conversational.",
    )
    headline: str = Field(
        max_length=40,
        description="Headline shown under the image — ≤40 chars.",
    )
    description: str | None = Field(
        default=None, max_length=125,
        description="Optional description shown below headline on some placements.",
    )
    interest_targeting: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Interest categories Meta supports — e.g. 'Personal finance', 'Books'.",
    )
    age_min: int = Field(ge=13, le=65, description="Minimum age.")
    age_max: int = Field(ge=13, le=65, description="Maximum age.")
    gender: str = Field(
        description="One of: 'any', 'male', 'female'. (Use 'any' unless the product is gender-specific.)",
    )


# ---------- Gemini client ----------

def _load_env_once():
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    env_path = Path(__file__).parent / "payload_pipeline" / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to Meta_Ads/payload_pipeline/.env"
        )
    try:
        from google import genai  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("google-genai is not installed.") from e
    return genai.Client(api_key=api_key)


def _model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


# ---------- Public API ----------

_RESOLVE_PROMPT = """You are resolving target cities for a Meta (Facebook + Instagram) ad campaign.

The user has chosen these cities to target:
{cities}

Business context:
  Business name: {business_name}
  Description:   {business_description}
  Country:       {country}
  Reach scope:   {reach_scope}

For each city return:
  • City + state/region label (e.g. "Bangalore, Karnataka")
  • Accurate city-centre latitude and longitude
  • A radius in KILOMETRES sensible for the business + scope:
      - "local"     → 3–10 km   (single-location service, dentist, salon)
      - "city-wide" → 10–25 km  (mid-size service or retail)
      - "metro"     → 25–60 km  (regional brand)
  • One short reason

Handle ambiguous names by picking the largest metro and noting it in the reason.
"""


def resolve_cities(
    city_names: list[str],
    *,
    business_name: str = "",
    business_description: str = "",
    country: str = "India",
    reach_scope: str = "city-wide",
) -> LocationGuess:
    """Resolve user-entered city names into lat/lng/radius_km for Meta targeting."""
    from google.genai import types  # type: ignore[import-not-found]
    client = _get_client()

    cities_block = "\n".join(f"  • {c}" for c in city_names)
    prompt = _RESOLVE_PROMPT.format(
        cities=cities_block,
        business_name=business_name or "(not provided)",
        business_description=business_description or "(not provided)",
        country=country,
        reach_scope=reach_scope,
    )
    resp = client.models.generate_content(
        model=_model(),
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LocationGuess,
        ),
    )
    if resp.parsed is None:
        raise RuntimeError(f"Resolver returned no parseable JSON:\n{resp.text}")
    return resp.parsed


_AD_COPY_PROMPT = """You are writing Meta (Facebook + Instagram) ad copy.

Business:
  Name: {business_name}
  About: {business_description}

Product / offer for this campaign:
  {product_description}

Currency: {currency}
Destination: {destination}     (Lead Form ads run inside Meta; Website ads send users out)
Default call-to-action: {default_cta}

Hard rules:
  • primary_text ≤ 500 chars, 2–3 short sentences, conversational, no emoji.
  • headline ≤ 40 chars — the hook.
  • description ≤ 125 chars (optional) — additional context.
  • interest_targeting: 3–5 Meta interest categories the audience cares about.
    Use simple plain-English (e.g. "Income tax", "Personal finance", "Books").
  • age_min / age_max: who actually buys this. Most products = 25–55.
  • gender: 'any' unless the product is unambiguously gendered.

Make the copy specific to the offer — no generic filler.
"""


def generate_ad_copy(
    *,
    business_name: str,
    business_description: str,
    product_description: str,
    currency: str,
    destination: str,
    default_cta: str,
) -> AdCopy:
    """Generate Meta ad copy + targeting hints for the campaign."""
    from google.genai import types  # type: ignore[import-not-found]
    client = _get_client()
    prompt = _AD_COPY_PROMPT.format(
        business_name=business_name or "(not provided)",
        business_description=business_description or "(not provided)",
        product_description=product_description or "(not provided)",
        currency=currency,
        destination=destination,
        default_cta=default_cta,
    )
    resp = client.models.generate_content(
        model=_model(),
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AdCopy,
        ),
    )
    if resp.parsed is None:
        raise RuntimeError(f"Ad copy gen returned no parseable JSON:\n{resp.text}")
    return resp.parsed


def to_epicenters(guess: LocationGuess) -> list[dict]:
    return [
        {"lat": c.lat, "lng": c.lng, "radius_km": c.radius_km, "name": c.name, "why": c.why}
        for c in guess.cities
    ]
