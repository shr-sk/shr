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

STRICT length limits (count characters carefully):
  • primary_text: 2-3 short sentences. MAXIMUM 400 characters TOTAL. No line breaks inside it.
  • headline: MAXIMUM 35 characters. The hook.
  • description: MAXIMUM 110 characters (optional). Additional context.
  • interest_targeting: exactly 3-5 Meta interest tags (e.g. "Income tax", "Personal finance").
  • age_min / age_max: integers, who actually buys this (typically 25-55).
  • gender: exactly one of "any", "male", "female".

Output rules:
  • No emoji, no \\n inside string values, no special characters that break JSON.
  • Make copy specific to the offer — no generic filler, no repetition.
  • Return ONE compact JSON object matching the schema. Do not exceed limits.
"""


_RUN_OF_WHITESPACE = None  # compiled lazily below


def _sanitize_string(s: str, max_chars: int) -> str:
    """Collapse runs of whitespace + truncate to max_chars.

    Defensive cleanup for when Gemini hits a degenerate loop and emits
    chains like '\\n\\n\\n...' or repeated tokens.
    """
    if not s:
        return ""
    global _RUN_OF_WHITESPACE
    if _RUN_OF_WHITESPACE is None:
        import re
        _RUN_OF_WHITESPACE = re.compile(r"\s+")
    cleaned = _RUN_OF_WHITESPACE.sub(" ", s).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + "…"
    return cleaned


def _sanitize_ad_copy_dict(raw: dict) -> dict:
    """Coerce a possibly-noisy LLM response dict into one that AdCopy can validate."""
    out = dict(raw)
    if "primary_text" in out:
        out["primary_text"] = _sanitize_string(out["primary_text"], 500)
    if "headline" in out:
        out["headline"] = _sanitize_string(out["headline"], 40)
    if out.get("description"):
        out["description"] = _sanitize_string(out["description"], 125)
    # Interests: max 8, dedup, strip
    if isinstance(out.get("interest_targeting"), list):
        seen = set()
        cleaned = []
        for item in out["interest_targeting"]:
            s = _sanitize_string(str(item), 60)
            if s and s.lower() not in seen:
                seen.add(s.lower())
                cleaned.append(s)
        out["interest_targeting"] = cleaned[:8]
    # Ages: clamp + integer
    try:
        out["age_min"] = max(13, min(65, int(out.get("age_min", 25))))
        out["age_max"] = max(13, min(65, int(out.get("age_max", 55))))
        if out["age_max"] < out["age_min"]:
            out["age_max"] = out["age_min"]
    except (TypeError, ValueError):
        out["age_min"] = 25
        out["age_max"] = 55
    # Gender: normalize
    g = str(out.get("gender", "any")).lower().strip()
    if g not in ("any", "male", "female"):
        g = "any"
    out["gender"] = g
    return out


def _call_gemini_for_copy(prompt: str):
    """Single attempt at structured output. Returns raw text + parsed (or None)."""
    from google.genai import types  # type: ignore[import-not-found]
    client = _get_client()
    return client.models.generate_content(
        model=_model(),
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AdCopy,
            # Generous cap — schema is small but structured output sometimes
            # spends extra tokens on JSON syntax / field names. Below this we
            # were occasionally truncating mid-value and producing invalid JSON.
            max_output_tokens=2048,
            temperature=0.7,
        ),
    )


def _fallback_ad_copy(
    business_name: str, business_description: str, product_description: str
) -> AdCopy:
    """Deterministic fallback when Gemini fails (truncation, rate limit, etc).

    Builds plausible Meta-ready copy from the raw inputs the user already
    typed. Not as polished as Gemini's output, but always returns valid copy
    so the launch flow doesn't dead-end.
    """
    # Primary text: lead with the product description, fall back to business desc
    primary_seed = (product_description or business_description or business_name or "").strip()
    primary = _sanitize_string(primary_seed, 400)
    if not primary:
        primary = f"Learn more about {business_name or 'us'}."

    # Headline: pull the first sentence of the product description (≤35 chars)
    first_sentence = (product_description or business_description or business_name).split(".")[0]
    headline = _sanitize_string(first_sentence, 35) or _sanitize_string(business_name, 35) or "Find out more"

    # Description: business positioning, truncated
    description = _sanitize_string(business_description or business_name, 110) or None

    return AdCopy(
        primary_text=primary,
        headline=headline,
        description=description,
        interest_targeting=[],   # let Meta auto-target rather than guess
        age_min=25,
        age_max=55,
        gender="any",
    )


def generate_ad_copy(
    *,
    business_name: str,
    business_description: str,
    product_description: str,
    currency: str,
    destination: str,
    default_cta: str,
) -> AdCopy:
    """Generate Meta ad copy + targeting hints, with sanitization + retry + fallback.

    Lifecycle:
      1. Call Gemini with structured output (try 1)
      2. If parsed OK → return
      3. If raw JSON parses → sanitize fields → validate → return
      4. If everything fails → try once more (handles transient Gemini hiccups)
      5. If still failing → return a deterministic fallback built from user input
         (never raises — the user is in mid-flow and shouldn't see "ad copy failed")
    """
    prompt = _AD_COPY_PROMPT.format(
        business_name=business_name or "(not provided)",
        business_description=business_description or "(not provided)",
        product_description=product_description or "(not provided)",
        currency=currency,
        destination=destination,
        default_cta=default_cta,
    )

    last_raw = ""
    for attempt in range(2):
        try:
            resp = _call_gemini_for_copy(prompt)
        except Exception:
            continue

        last_raw = getattr(resp, "text", "") or ""

        # Path 1 — Gemini's strict parser succeeded.
        # Still sanitize: Gemini occasionally emits real newlines INSIDE strings
        # (valid JSON, passes Pydantic's max_length, but renders ugly in ads).
        if getattr(resp, "parsed", None) is not None:
            cleaned = _sanitize_ad_copy_dict(resp.parsed.model_dump())
            return AdCopy.model_validate(cleaned)

        # Path 2 — JSON is well-formed but failed schema validation → sanitize
        try:
            import json as _json
            raw_dict = _json.loads(last_raw)
            cleaned = _sanitize_ad_copy_dict(raw_dict)
            return AdCopy.model_validate(cleaned)
        except Exception:
            continue

    # Path 3 — every Gemini attempt failed (truncation, rate limit, schema reject).
    # Return a fallback so the flow never dies. Caller sees normal ad copy with
    # interest_targeting=[] which is a soft signal it's a fallback.
    return _fallback_ad_copy(business_name, business_description, product_description)


def to_epicenters(guess: LocationGuess) -> list[dict]:
    return [
        {"lat": c.lat, "lng": c.lng, "radius_km": c.radius_km, "name": c.name, "why": c.why}
        for c in guess.cities
    ]
