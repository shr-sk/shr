"""Static lookups + currency-aware presets for the Meta Ads dashboard.

Two operating modes:
  • USD — US-based clients; geo prefill = New York; budget in dollars
  • INR — India-based clients; geo prefill = Bangalore; budget in rupees

The sidebar toggle on every page sets ss.currency to one of these. All
downstream defaults branch on that single flag.
"""
from __future__ import annotations


# ---------- Currency ----------

CURRENCY_CHOICES = ["USD", "INR"]

CURRENCY = {
    "USD": {
        "code": "USD",
        "symbol": "$",
        # Meta stores money in MINOR currency units (cents / paise).
        "minor_per_unit": 100,
        "country_iso": "US",
        "default_geo_city": "New York, NY",
        "default_daily_budget": 20.0,
        "default_spend_cap_multiplier": 30,
    },
    "INR": {
        "code": "INR",
        "symbol": "₹",
        "minor_per_unit": 100,
        "country_iso": "IN",
        "default_geo_city": "Bangalore, Karnataka",
        "default_daily_budget": 500.0,
        "default_spend_cap_multiplier": 30,
    },
}


def to_minor(amount: float, currency: str) -> int:
    """Convert a major-unit amount ($10 / ₹500) to minor units (1000 / 50000)."""
    return int(round(amount * CURRENCY[currency]["minor_per_unit"]))


def sym(currency: str) -> str:
    return CURRENCY[currency]["symbol"]


# ---------- Geo presets ----------

# Friendly name -> ISO 3166-1 alpha-2 (what Meta expects in geo_locations.countries)
COUNTRY_TO_ISO = {
    "United States": "US",
    "India":         "IN",
    "Canada":        "CA",
    "United Kingdom": "GB",
}

# Default country per currency
CURRENCY_TO_COUNTRY = {"USD": "United States", "INR": "India"}


# Meta locale IDs — used by ad_set.targeting.locales
# Full list: https://www.facebook.com/business/help/216347487705352
LANGUAGE_TO_LOCALES = {
    "English":  [6],   # English (US) — Meta locale 6 covers en_US
    "Hindi":    [46],
    "Spanish":  [23],
    "French":   [9],
}


# ---------- Gender ----------

# Meta targeting.genders: 1 = men, 2 = women, []/null = all
GENDER_TO_META = {
    "Any":         [],
    "Female only": [2],
    "Male only":   [1],
}


# ---------- Destination / CTA ----------

DESTINATION_CHOICES = ["Website", "Lead Form"]

# CTA enums available per destination — pulled from Meta's CallToActionType enum.
CTA_FOR_WEBSITE = [
    "SHOP_NOW", "LEARN_MORE", "SIGN_UP", "DOWNLOAD", "GET_OFFER",
    "GET_QUOTE", "CONTACT_US", "BUY_NOW", "BOOK_TRAVEL", "SUBSCRIBE",
]
CTA_FOR_LEAD_FORM = [
    "GET_QUOTE", "SIGN_UP", "LEARN_MORE", "CONTACT_US", "APPLY_NOW",
    "GET_OFFER", "SUBSCRIBE", "DOWNLOAD",
]


# ---------- Bidding ----------

BIDDING_OPTIONS = [
    ("Lowest cost (auto)",         "LOWEST_COST_WITHOUT_CAP"),
    ("Lowest cost with bid cap",   "LOWEST_COST_WITH_BID_CAP"),
    ("Cost cap",                   "COST_CAP"),
]


# ---------- Media spec ----------
# Per-placement dimensions. Same image can serve multiple slots when aspect matches.
#
# Slot label · required · dimensions · aspect · notes

MEDIA_SPEC_BASE = [
    ("Feed (square)",   True,  "1080x1080",  "1:1",    "FB Feed + IG Feed — required"),
    ("Feed (portrait)", False, "1080x1350",  "4:5",    "IG Feed portrait — recommended"),
    ("Stories / Reels", False, "1080x1920",  "9:16",   "FB Stories + IG Stories + Reels"),
    ("Right column",    False, "1200x628",   "1.91:1", "FB right column + Audience Network"),
    ("Video (Reels)",   False, "1080x1920",  "9:16",   "Optional video — Reels + Stories"),
]


# ---------- Business presets — change UI defaults based on currency ----------

CUSTOM_KEY = "Custom (describe below)"

PRESETS_USD = {
    CUSTOM_KEY: {
        "category": "",
        "default_cta": "LEARN_MORE",
    },
    "E-commerce / online store": {
        "category": "Retail",
        "default_cta": "SHOP_NOW",
    },
    "Local restaurant / cafe": {
        "category": "Food & Drink",
        "default_cta": "GET_OFFER",
    },
    "Fitness studio / gym": {
        "category": "Fitness",
        "default_cta": "SIGN_UP",
    },
    "Dental / medical practice": {
        "category": "Healthcare",
        "default_cta": "BOOK_TRAVEL",
    },
}

PRESETS_INR = {
    CUSTOM_KEY: {
        "category": "",
        "default_cta": "LEARN_MORE",
    },
    "Chartered Accountant / Tax consultant": {
        "category": "Professional Services",
        "default_cta": "GET_QUOTE",
    },
    "Coaching / Tuition centre": {
        "category": "Education",
        "default_cta": "SIGN_UP",
    },
    "Restaurant / Cloud kitchen": {
        "category": "Food & Drink",
        "default_cta": "GET_OFFER",
    },
    "Salon / Wellness": {
        "category": "Beauty & Personal Care",
        "default_cta": "SIGN_UP",
    },
}


def presets_for(currency: str) -> dict:
    return PRESETS_INR if currency == "INR" else PRESETS_USD


# ---------- Prefilled scenario per currency ----------
# These get auto-filled into the Create form so testing only needs media.

SCENARIOS = {
    "USD": {
        "preset_label": "E-commerce / online store",
        "business_name": "Brooklyn Reads",
        "website_url": "https://brooklynreads.com",
        "business_description": (
            "Independent bookstore in Brooklyn, New York. Curated fiction, "
            "philosophy, and rare editions. Free shipping nationwide on "
            "orders over $35."
        ),
        "ad_account_id": "204512345678901",
        "page_id": "100000000000001",
        "instagram_actor_id": "",
        "product_description": (
            "Spring 2026 fiction collection — 15 debut novels and "
            "award-winning hardcovers, $18–$28."
        ),
        "city": "New York, NY",
        "daily_budget": 20.0,
        "destination": "Website",
        "default_cta": "SHOP_NOW",
    },
    "INR": {
        "preset_label": "Chartered Accountant / Tax consultant",
        "business_name": "Kapoor & Associates — Chartered Accountants",
        "website_url": "",  # CA has no website — Instant Form only
        "business_description": (
            "Bangalore-based Chartered Accountant firm with 15+ years of "
            "experience. ITR filing, tax planning, GST compliance, and audit "
            "services for salaried professionals and business owners. "
            "Personalised review by licensed CAs — no DIY mistakes, no "
            "missed deductions."
        ),
        "ad_account_id": "204512345678902",
        "page_id": "100000000000002",
        "instagram_actor_id": "",
        "product_description": (
            "Income Tax Return filing for AY 2026-27 (FY 2025-26). "
            "Filing deadline 31 July 2026 — avoid ₹5,000 late fee + "
            "interest under Section 234A. Personalised tax planning, "
            "deduction optimisation (80C, 80D, HRA, home loan), and "
            "expert review. Starting from ₹999 for salaried filing."
        ),
        "city": "Bangalore, Karnataka",
        "daily_budget": 600.0,
        "destination": "Lead Form",
        "default_cta": "GET_QUOTE",
    },
}


def scenario_for(currency: str) -> dict:
    return SCENARIOS.get(currency, SCENARIOS["USD"])
