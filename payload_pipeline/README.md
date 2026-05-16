# Meta Ads launcher (v1: Traffic objective, single-image ad, mock-first)

Turns a hand-written YAML into a sequence of Meta Marketing API create-calls,
defaulting to a mock adapter that prints what *would* be sent.

## Files

| File | Role |
|------|------|
| `inputs/*.yaml` | Hand-written campaign specs |
| `schemas.py`    | Pydantic models — the contract for the YAML |
| `validate.py`   | YAML → Pydantic, with beginner-friendly error messages |
| `builders.py`   | Pydantic → ordered list of create-operations |
| `adapters.py`   | Either prints (`mock`) or sends (`meta`, stub) |
| `launch.py`     | CLI entry point |

## Run — three modes

```
# 1) Mock — no API calls, no credentials. Default.
python launch.py inputs/example_traffic_campaign.yaml --adapter mock

# 2) Validate-only — real API call, real auth, but Meta does NOT create.
#    Confirms your payload would be accepted before creating real campaigns.
python launch.py inputs/example_traffic_campaign.yaml --adapter meta --validate-only

# 3) Live — creates campaign at status=PAUSED. Human flips to ACTIVE in Ads Manager.
python launch.py inputs/example_traffic_campaign.yaml --adapter meta
```

## Upload a poster image first → get the `image_hash`

Meta link-ads can't reference a local file path — the image must be
uploaded first, and you put the returned `image_hash` into the YAML.

```
# Mock — deterministic MD5-of-file hash, no creds needed (useful for YAML wiring).
python upload_image.py /path/to/poster.jpg --ad-account-id 1234567890

# Live — uploads to Meta and returns the real hash.
python upload_image.py /path/to/poster.jpg --ad-account-id 1234567890 --adapter meta
```

The hash is printed both to stderr (human summary) and stdout (JSON, for scripting). Paste it into your YAML:

```yaml
ad:
  creative:
    object_story_spec:
      link_data:
        image_hash: "<paste here>"
```

## Credentials (modes 2 + 3 only)

1. Copy `.env.example` → `.env`.
2. Fill `META_ACCESS_TOKEN` (long-lived token from Events Manager or a system-user token from Business Settings).
3. `.env` is gitignored — never commit.

Setup paths if you don't have a token yet:
- For quick start: Events Manager → Settings → Generate Access Token (60-day expiry).
- For production: Business Settings → System Users → Generate token with `ads_management` scope (no expiry).
- Test ads: [Meta's developer mode](https://developers.facebook.com/docs/marketing-api/test-accounts) lets you create test ad accounts that don't burn real money.

## Pilot guard — conversion objectives

Smart-delivery objectives (`OUTCOME_SALES`, `OUTCOME_LEADS`) and conversion optimization goals (`OFFSITE_CONVERSIONS`, `VALUE`, `LEAD_GENERATION`, `QUALITY_LEAD`) require working Pixel + CAPI to be meaningful. The live adapter blocks them with a friendly error unless you set:

```
CONVERSION_TRACKING_VERIFIED=true
```

in your environment. For the pilot phase, use `OUTCOME_TRAFFIC` with `LINK_CLICKS` optimization — it doesn't need conversion tracking to function.

## v1 scope

- Objective: `OUTCOME_TRAFFIC` (does not require Pixel — safe before Step 2)
- One campaign → one ad set → one single-image link ad
- Targeting: geo_locations, age, genders, locales, flexible_spec (interests), publisher/positions
- Status: always `PAUSED`

Out of v1: carousels (`child_attachments`), DCO (`asset_feed_spec`), Advantage+ creative,
custom audiences upload flow, video ads, DPA, Outcome_Sales (needs Pixel/CAPI first), iOS SKAdNetwork.

## Pre-launch checklist (when you eventually wire the real adapter)

1. `image_hash` — must come from a prior `POST /act_{id}/adimages` upload.
2. `page_id`, `instagram_actor_id` — IDs of the Page / IG account the ad runs from.
3. `dsa_payor` / `dsa_beneficiary` — required if any EU placement.
4. Pixel ID + CAPI events working (Step 2) — required before switching objective to `OUTCOME_SALES`.
