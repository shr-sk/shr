"""Pydantic models for the Meta Ads launcher YAML.

Three-tier hierarchy: campaign -> ad_set -> ad. The YAML mirrors that
shape; field names match the Marketing API where reasonable.

Only v1 fields are exposed (OUTCOME_TRAFFIC objective, single-image link
ad, basic targeting). Other objectives and creative types are out of scope.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------- Level 1: Campaign ----------

Objective = Literal[
    "OUTCOME_TRAFFIC", "OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT",
    "OUTCOME_LEADS", "OUTCOME_APP_PROMOTION", "OUTCOME_SALES",
]
SpecialAdCategory = Literal[
    "NONE", "HOUSING", "EMPLOYMENT", "CREDIT",
    "ISSUES_ELECTIONS_POLITICS", "ONLINE_GAMBLING_AND_GAMING",
    "FINANCIAL_PRODUCTS_SERVICES",
]


LaunchStatus = Literal["PAUSED", "ACTIVE"]


class CampaignInput(BaseModel):
    name: str
    objective: Objective = "OUTCOME_TRAFFIC"
    # Initial status — PAUSED is the safe default; ACTIVE starts spending immediately.
    # Applies to campaign / ad_set / ad in this YAML render (we set them together).
    status: LaunchStatus = "PAUSED"
    special_ad_categories: list[SpecialAdCategory] = Field(default_factory=lambda: ["NONE"])
    special_ad_category_country: list[str] | None = None
    buying_type: Literal["AUCTION", "RESERVATION"] = "AUCTION"
    # Safety rail — hard ceiling in minor currency units (e.g. paise, cents).
    spend_cap: int | None = Field(default=None, ge=0)
    # Set only if using Advantage+ Campaign Budget (CBO); otherwise put budget on ad_set.
    daily_budget: int | None = Field(default=None, ge=0)
    lifetime_budget: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_category_country(self):
        non_none = [c for c in self.special_ad_categories if c != "NONE"]
        if non_none and not self.special_ad_category_country:
            raise ValueError(
                "special_ad_category_country is required when special_ad_categories includes a non-NONE value"
            )
        if self.daily_budget and self.lifetime_budget:
            raise ValueError("set only one of daily_budget or lifetime_budget at campaign level")
        return self


# ---------- Level 2: Ad Set ----------

OptimizationGoal = Literal[
    "LINK_CLICKS", "IMPRESSIONS", "REACH", "LANDING_PAGE_VIEWS",
    "OFFSITE_CONVERSIONS", "VALUE", "THRUPLAY", "LEAD_GENERATION",
    "APP_INSTALLS",
]
BillingEvent = Literal["IMPRESSIONS", "LINK_CLICKS", "THRUPLAY", "APP_INSTALLS"]
BidStrategy = Literal[
    "LOWEST_COST_WITHOUT_CAP", "LOWEST_COST_WITH_BID_CAP",
    "COST_CAP", "LOWEST_COST_WITH_MIN_ROAS",
]
Platform = Literal["facebook", "instagram", "messenger", "audience_network"]
DestinationType = Literal[
    "WEBSITE", "APP", "MESSENGER", "INSTAGRAM_DIRECT",
    "WHATSAPP", "ON_AD", "ON_POST",
]


class CustomLocation(BaseModel):
    # Drop a pin at lat/lng with a radius. Maps directly to Meta's
    # targeting.geo_locations.custom_locations entries.
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius: float = Field(gt=0)
    distance_unit: Literal["kilometer", "mile"] = "kilometer"


class GeoLocations(BaseModel):
    countries: list[str] = Field(default_factory=list)  # ISO 3166-1 alpha-2, e.g. "IN"
    cities: list[dict] = Field(default_factory=list)
    regions: list[dict] = Field(default_factory=list)
    custom_locations: list[CustomLocation] = Field(default_factory=list)
    # location_types controls home vs. recent vs. travel_in — defaults to home+recent.
    location_types: list[Literal["home", "recent", "travel_in"]] = Field(
        default_factory=lambda: ["home", "recent"]
    )


class InterestEntry(BaseModel):
    id: str
    name: str | None = None


class FlexibleSpecBlock(BaseModel):
    interests: list[InterestEntry] = Field(default_factory=list)
    behaviors: list[InterestEntry] = Field(default_factory=list)


class TargetingAutomation(BaseModel):
    """Meta requires this field on every ad set since 2024 — explicit
    on/off for Advantage Audience (Meta's AI audience expansion).

    `advantage_audience = 1` lets Meta expand beyond your specified targeting
    if it predicts better results. `0` keeps delivery strict to what you set.

    For Lead Form ads with tight geo (single-city), 0 is usually the right
    pick — preserves the local-only delivery. For broad-reach campaigns,
    1 tends to perform better.
    """
    advantage_audience: int = Field(default=0, ge=0, le=1)


class TargetingInput(BaseModel):
    geo_locations: GeoLocations
    age_min: int = Field(default=18, ge=13, le=65)
    age_max: int = Field(default=65, ge=13, le=65)
    # [1]=male, [2]=female, []=all
    genders: list[int] = Field(default_factory=list)
    locales: list[int] = Field(default_factory=list)
    flexible_spec: list[FlexibleSpecBlock] = Field(default_factory=list)
    publisher_platforms: list[Platform] = Field(default_factory=lambda: ["facebook", "instagram"])
    facebook_positions: list[str] | None = None
    instagram_positions: list[str] | None = None
    targeting_automation: TargetingAutomation = Field(default_factory=TargetingAutomation)

    @model_validator(mode="after")
    def check_age(self):
        if self.age_max < self.age_min:
            raise ValueError("targeting.age_max must be >= age_min")
        return self


class PromotedObject(BaseModel):
    pixel_id: str | None = None
    custom_event_type: str | None = None
    application_id: str | None = None
    object_store_url: str | None = None
    page_id: str | None = None


class AdSetInput(BaseModel):
    name: str
    optimization_goal: OptimizationGoal = "LINK_CLICKS"
    billing_event: BillingEvent = "IMPRESSIONS"
    bid_strategy: BidStrategy = "LOWEST_COST_WITHOUT_CAP"
    bid_amount: int | None = Field(default=None, ge=0)
    daily_budget: int | None = Field(default=None, ge=0)
    lifetime_budget: int | None = Field(default=None, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    destination_type: DestinationType = "WEBSITE"
    promoted_object: PromotedObject | None = None
    targeting: TargetingInput
    # EU Digital Services Act — Marketing API rejects EU placements without these.
    dsa_payor: str | None = None
    dsa_beneficiary: str | None = None

    @model_validator(mode="after")
    def check_budget_and_time(self):
        # v1 puts the budget on the ad set (no campaign-budget optimization).
        if self.daily_budget is None and self.lifetime_budget is None:
            raise ValueError(
                "ad_set must declare daily_budget or lifetime_budget "
                "(campaign-budget optimization is not in v1)"
            )
        if self.daily_budget and self.lifetime_budget:
            raise ValueError("set only one of daily_budget or lifetime_budget on ad_set")
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("ad_set.end_time must be after start_time")
        return self


# ---------- Level 3: Ad (single-image link ad) ----------

CallToActionType = Literal[
    "SHOP_NOW", "LEARN_MORE", "SIGN_UP", "BOOK_TRAVEL", "DOWNLOAD",
    "GET_OFFER", "CONTACT_US", "APPLY_NOW", "SUBSCRIBE", "DONATE_NOW",
    "ORDER_NOW", "GET_QUOTE", "BUY_NOW", "INSTALL_APP",
]


class CallToAction(BaseModel):
    type: CallToActionType
    # The CTA's own destination; usually equal to link_data.link.
    value_link: str | None = None
    # Set this instead of value_link when destination_type is ON_AD
    # (Meta Instant Form). Must be a real form_id from a prior
    # `POST /page/<page_id>/leadgen_forms` call.
    value_lead_gen_form_id: str | None = None


class LinkData(BaseModel):
    # image_hash must come from a prior /adimages upload.
    # Used for FB Feed + IG Feed (recommended ratio 1:1, e.g. 1080x1080).
    image_hash: str
    # Optional placement-specific variants — when present, the builder emits
    # Meta's `asset_feed_spec` with `asset_customization_rules` so each
    # placement gets its best-fitting image.
    image_hash_story: str | None = None       # 9:16 — for Stories + Reels
    image_hash_portrait: str | None = None    # 4:5  — IG Feed portrait
    message: str   # primary text
    name: str      # headline
    description: str | None = None
    link: str
    call_to_action: CallToAction


class ObjectStorySpec(BaseModel):
    page_id: str
    instagram_actor_id: str | None = None
    link_data: LinkData


class AdCreativeInput(BaseModel):
    name: str | None = None
    object_story_spec: ObjectStorySpec
    url_tags: str | None = None


class AdInput(BaseModel):
    name: str
    creative: AdCreativeInput


# ---------- Lead form spec (when destination_type=ON_AD) ----------

PrefilledQuestion = Literal[
    "FULL_NAME", "FIRST_NAME", "LAST_NAME",
    "EMAIL", "PHONE", "PHONE_NUMBER",
    "CITY", "STATE", "COUNTRY", "POST_CODE",
    "GENDER", "DOB",
]


class LeadFormSpec(BaseModel):
    """Configuration for a Meta Instant Form (LeadGenForm).

    The launcher posts to `/page/<page_id>/leadgen_forms` BEFORE creating
    the ad, then swaps the form_id back into the ad creative.
    """
    name: str
    privacy_url: str
    thank_you_message: str = "Thanks! We'll be in touch."
    custom_questions: list[str] = Field(default_factory=list)
    prefilled_questions: list[PrefilledQuestion] = Field(
        default_factory=lambda: ["FULL_NAME", "EMAIL", "PHONE_NUMBER"]
    )
    locale: str = "en_US"


# ---------- Root YAML ----------

class MetaCampaignYaml(BaseModel):
    # Digits only — the launcher prepends `act_` where the API needs it.
    ad_account_id: str
    campaign: CampaignInput
    ad_set: AdSetInput
    ad: AdInput
    # Present only when destination_type=ON_AD (Lead Form ads). Consumed by
    # the launcher BEFORE ad creation to POST /page/{page_id}/leadgen_forms.
    lead_form: LeadFormSpec | None = None
