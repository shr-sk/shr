"""Create campaign view — currency toggle, Pixel install modal, prefill switch."""
from __future__ import annotations

import sys
import uuid
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "payload_pipeline"))

import streamlit as st
import yaml

from auth.gate import gate

me = gate()

from llm_resolver import _load_env_once, generate_ad_copy, resolve_cities, to_epicenters
from upload_image import upload_live, upload_mock  # type: ignore[import-not-found]
from presets import (
    BIDDING_OPTIONS,
    CTA_FOR_LEAD_FORM,
    CTA_FOR_WEBSITE,
    CURRENCY,
    CURRENCY_CHOICES,
    CURRENCY_TO_COUNTRY,
    DESTINATION_CHOICES,
    MEDIA_SPEC_BASE,
    presets_for,
    scenario_for,
)
from styles import hero, inject_css, section_label
from yaml_render import build_meta_yaml

inject_css()

_load_env_once()

UPLOADS_DIR = ROOT / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


# ============================================================================
# Pixel install snippet (USED IN THE MODAL — Purchase event only as requested)
# ============================================================================

_PIXEL_BASE = """<!-- Meta Pixel — paste in <head> of every page -->
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'YOUR_PIXEL_ID');
fbq('track', 'PageView');
</script>"""

_PIXEL_PURCHASE = """<!-- Paste ONLY on the order-confirmation / thank-you page -->
<script>
fbq('track', 'Purchase', {
  value: 47.50,        // ← actual revenue (number, not string)
  currency: 'USD',     // ← match your ad account currency
  content_ids: ['SKU-12345'],
  content_type: 'product'
});
</script>"""


# ============================================================================
# Session state seeds
# ============================================================================

ss = st.session_state
ss.setdefault("currency", "USD")
ss.setdefault("rendered_yaml", None)
ss.setdefault("mock_output", "")
ss.setdefault("ad_copy", None)
ss.setdefault("epicenters", [])
ss.setdefault("uploaded_files", {})
ss.setdefault("pixel_id", "")
ss.setdefault("pixel_modal_acknowledged", False)
ss.setdefault("prev_destination", None)


def _safe_label(label: str) -> str:
    """Filesystem-safe slug. Slot labels like "Stories / Reels" or
    "Feed (square)" contain `/`, `(`, `)`, spaces — strip everything except
    alphanumerics, collapse to underscore, trim trailing separators."""
    import re
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "slot"


def _save_upload(uploaded_file, label: str) -> str:
    # `label` here may still contain unsafe characters from the slot name;
    # always re-sanitise before using it as a filename component.
    safe = _safe_label(label)
    suffix = Path(uploaded_file.name).suffix
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOADS_DIR / f"{safe}_{uuid.uuid4().hex[:8]}{suffix}"
    with open(target, "wb") as f:
        f.write(uploaded_file.getvalue())
    return str(target)


# ============================================================================
# Sidebar — currency toggle
# ============================================================================

with st.sidebar:
    ss.currency = st.radio("Currency", CURRENCY_CHOICES, horizontal=True, index=CURRENCY_CHOICES.index(ss.currency))
    sym = CURRENCY[ss.currency]["symbol"]
    st.caption(f"Country: {CURRENCY_TO_COUNTRY[ss.currency]}")


# Pull scenario defaults for the active currency
scenario = scenario_for(ss.currency)
presets = presets_for(ss.currency)


hero(
    "Create campaign",
    kicker="Step 1 of 3",
    subtitle="Configure destination, audience, and creatives. Build, preview, then launch when ready.",
)


# ============================================================================
# A. Destination + Client
# ============================================================================
section_label("Destination & client")

c1, c2 = st.columns([1, 2])
with c1:
    destination = st.radio(
        "Destination",
        DESTINATION_CHOICES,
        index=DESTINATION_CHOICES.index(scenario["destination"]),
        help="Website = drive to landing page (needs Pixel). Lead Form = capture leads inside Meta.",
    )

# Detect transition to Website to trigger Pixel modal once
just_switched_to_website = (
    destination == "Website" and ss.prev_destination != "Website"
)
ss.prev_destination = destination

with c2:
    preset_labels = list(presets.keys())
    default_preset_idx = preset_labels.index(scenario["preset_label"]) if scenario["preset_label"] in preset_labels else 0
    a, b = st.columns(2)
    preset_label = a.selectbox("Preset", preset_labels, index=default_preset_idx)
    business_name = b.text_input("Business name", value=scenario["business_name"])
    a, b = st.columns(2)
    website_url = a.text_input(
        "Website URL",
        value=scenario["website_url"],
        placeholder=("https://example.com" if destination == "Website" else "(not needed for Lead Form)"),
    )
    b.empty()

business_description = st.text_area(
    "About the business",
    value=scenario["business_description"],
    height=110,
)


# ============================================================================
# A.5 — Pixel install modal (only for Website destination)
# ============================================================================
if destination == "Website" and (just_switched_to_website or not ss.pixel_modal_acknowledged):
    with st.container(border=True):
        st.markdown("### Install Meta Pixel for conversion tracking")
        st.markdown(
            "**Without Pixel**, you'll see clicks, CTR, and CPC — "
            "**but not CAC, ROAS, or conversion rate.** "
            "Install before launching to track revenue back to ads."
        )

        with st.expander("Step 1 — Generate Pixel ID (1 minute)", expanded=False):
            st.markdown(
                "1. Go to **events.facebook.com**\n"
                "2. Pick your **Business → Data sources → Web → Create a new dataset**\n"
                "3. Enter a name (e.g. *Brooklyn Reads Pixel*)\n"
                "4. Copy the 15-digit **Pixel ID** that appears"
            )

        with st.expander("Step 2 — Paste base snippet in `<head>` of every page", expanded=False):
            st.caption("Replace `YOUR_PIXEL_ID` with the ID from Step 1.")
            st.code(_PIXEL_BASE, language="html")

        with st.expander("Step 3 — Paste Purchase snippet on order-confirmation page ONLY", expanded=True):
            st.caption(
                "This is the single event that powers CAC and ROAS. Fires when a real order completes "
                "(the thank-you page after payment), NOT on the checkout page."
            )
            st.code(_PIXEL_PURCHASE, language="html")

        c1, c2, c3 = st.columns([2, 1, 1])
        ss.pixel_id = c1.text_input("Already have a Pixel ID?", value=ss.pixel_id, placeholder="15-digit Pixel ID")
        if c2.button("Skip for now"):
            ss.pixel_modal_acknowledged = True
            st.rerun()
        if c3.button("Save & continue", type="primary"):
            ss.pixel_modal_acknowledged = True
            st.rerun()

    st.stop()

# Banner if user skipped Pixel install
if destination == "Website" and not ss.pixel_id:
    st.warning(
        "**Pixel not installed.** Only reach metrics (CTR / CPC / impressions) will be tracked. "
        "CAC and ROAS will be unavailable until Pixel + Purchase event are live."
    )


st.divider()


# ============================================================================
# B. Account IDs
# ============================================================================
section_label("Account")
c1, c2, c3 = st.columns(3)
ad_account_id = c1.text_input("Ad Account ID", value=scenario["ad_account_id"])
page_id = c2.text_input("Facebook Page ID", value=scenario["page_id"])
instagram_actor_id = c3.text_input("Instagram Actor ID", value=scenario.get("instagram_actor_id", ""), placeholder="optional")

st.divider()


# ============================================================================
# C. Product
# ============================================================================
section_label("Product")
product_description = st.text_area(
    "What this campaign promotes",
    value=scenario["product_description"],
    height=110,
)
st.divider()


# ============================================================================
# D. Media
# ============================================================================
section_label("Media")
media_cols = st.columns(min(len(MEDIA_SPEC_BASE), 3))
for i, (label, required, size, aspect, notes) in enumerate(MEDIA_SPEC_BASE):
    col = media_cols[i % len(media_cols)]
    with col:
        tag = "Required" if required else "Optional"
        st.markdown(f"**{label}**  \n`{size}` · {aspect} · {tag}")
        ftypes = ["mp4", "mov"] if "Video" in label else ["png", "jpg", "jpeg", "webp"]
        uploaded = st.file_uploader(
            label, type=ftypes, key=f"upload-{label}", label_visibility="collapsed",
        )
        if uploaded:
            slug = _safe_label(label)
            path = _save_upload(uploaded, slug)
            ss.uploaded_files[label] = {
                "label": slug,
                "local_path": path,
                "aspect": aspect,
                "kind": "video" if "Video" in label else "image",
            }
            st.caption("Saved")
st.divider()


# ============================================================================
# E. Targeting
# ============================================================================
section_label("Targeting")
cities_text = st.text_input("Target cities — comma separated", value=scenario["city"])
reach_scope = st.radio(
    "Scope per city",
    ["local", "city-wide", "metro"],
    index=1,
    horizontal=True,
)
st.divider()


# ============================================================================
# F. Budget
# ============================================================================
section_label("Budget")
c1, c2, c3 = st.columns(3)
daily_budget = c1.number_input(
    f"Daily {sym}", min_value=1.0, value=scenario["daily_budget"], step=5.0 if ss.currency == "USD" else 50.0,
)
bidding_label = c2.selectbox("Bidding", [label for label, _ in BIDDING_OPTIONS])
bidding = dict(BIDDING_OPTIONS)[bidding_label]

cta_list = CTA_FOR_LEAD_FORM if destination == "Lead Form" else CTA_FOR_WEBSITE
default_cta = scenario.get("default_cta", cta_list[0])
default_cta_idx = cta_list.index(default_cta) if default_cta in cta_list else 0
cta_type = c3.selectbox("Call to action", cta_list, index=default_cta_idx)

c1, c2 = st.columns(2)
c1.caption(f"~{sym}{daily_budget * 30:,.0f}/mo")

# Lead form config (only for Lead Form destination)
lead_form_config = None
if destination == "Lead Form":
    with st.expander("Lead form config", expanded=False):
        c1, c2 = st.columns(2)
        lf_name = c1.text_input("Form name", value=f"{business_name} — Lead form")
        lf_privacy = c2.text_input("Privacy policy URL", value="https://example.com/privacy")
        lf_thanks = st.text_input("Thank-you message", value="Thanks! We'll be in touch within 24 hours.")
        questions = st.multiselect(
            "Prefilled questions",
            ["FULL_NAME", "EMAIL", "PHONE_NUMBER", "CITY", "STATE", "COUNTRY", "POST_CODE", "DOB"],
            default=["FULL_NAME", "EMAIL", "PHONE_NUMBER"],
        )
        lead_form_config = {
            "name": lf_name,
            "privacy_url": lf_privacy,
            "thank_you_message": lf_thanks,
            "custom_questions": [],
            "prefilled_questions": questions,
            "locale": "en_US",
        }

st.divider()


# ============================================================================
# Build + Launch
# ============================================================================

ss.setdefault("confirm_active_launch", False)
ss.setdefault("launch_result", "")
ss.setdefault("launch_error", "")

section_label("Build & launch")

# Launch status — applies when the YAML is built AND when launching live.
# PAUSED is the safe default; ACTIVE starts spending within ~30 min on Meta.
launch_status = st.radio(
    "Launch status",
    ["PAUSED", "ACTIVE"],
    index=0,
    horizontal=True,
    help=(
        "PAUSED  — campaign is created but not delivering. You can review on Meta or "
        "flip Resume in the Manage tab.  "
        "ACTIVE — campaign starts spending immediately (within ~30 min)."
    ),
)
ss["launch_status"] = launch_status

btn_build, btn_mock, btn_live = st.columns(3)


def _problems() -> list[str]:
    p = []
    if not business_name: p.append("Business name required.")
    if not business_description: p.append("Business description required.")
    if not ad_account_id: p.append("Ad Account ID required.")
    if not page_id: p.append("Facebook Page ID required.")
    if not product_description: p.append("Product description required.")
    if destination == "Website" and not website_url:
        p.append("Website URL required for Website destination.")
    return p


def _image_paths_by_aspect():
    """Return uploaded image dicts grouped by aspect.

    Streamlit Cloud's filesystem is ephemeral — files inside `uploads/` get
    wiped on every redeploy/restart. We auto-purge any session-state entries
    whose local files no longer exist, so the user gets a clear "re-upload"
    state instead of a silent failure later in the pipeline.
    """
    out: dict[str, dict] = {}
    dead_keys = [
        k for k, v in ss.uploaded_files.items()
        if not Path(v.get("local_path", "")).exists()
    ]
    if dead_keys:
        for k in dead_keys:
            del ss.uploaded_files[k]
        st.warning(
            f"{len(dead_keys)} previously-uploaded file(s) are no longer on the "
            f"server (Streamlit Cloud wipes uploads on every restart). Please "
            f"re-upload them above and click Build YAML again."
        )
    for entry in ss.uploaded_files.values():
        if entry["kind"] != "image":
            continue
        out[entry["aspect"]] = entry
    return out


# Hash cache — avoid re-uploading the same file when user clicks Build YAML twice.
# Keyed by (local_path, mode) so flipping demo mode forces a re-upload (different
# hashes — MD5 vs real Meta hash).
ss.setdefault("image_hash_cache", {})


def _ensure_image_hash(entry: dict, ad_account_id: str, use_mock: bool) -> str | None:
    """Upload an image file → return its image_hash.

    Uses ss.image_hash_cache to skip duplicate uploads. Returns None on
    error (caller decides whether that's fatal).
    """
    local_path = Path(entry["local_path"])
    if not local_path.exists():
        return None

    cache_key = (str(local_path), "mock" if use_mock else "live")
    if cache_key in ss.image_hash_cache:
        return ss.image_hash_cache[cache_key]

    try:
        if use_mock:
            result = upload_mock(local_path, ad_account_id)
        else:
            result = upload_live(local_path, ad_account_id)
        h = result.get("image_hash")
        if h:
            ss.image_hash_cache[cache_key] = h
        return h
    except Exception as e:
        st.error(f"Image upload failed for {local_path.name}: {e}")
        return None


if btn_build.button("Build YAML", type="primary", use_container_width=True):
    problems = _problems()
    if problems:
        for x in problems:
            st.error(x)
    else:
        client = {
            "business_name": business_name,
            "website_url": website_url,
            "ad_account_id": ad_account_id.replace("-", "").strip(),
            "page_id": page_id.strip(),
            "instagram_actor_id": instagram_actor_id.strip(),
        }
        try:
            city_names = [c.strip() for c in cities_text.split(",") if c.strip()]
            if city_names:
                with st.spinner("Resolving locations…"):
                    guess = resolve_cities(
                        city_names,
                        business_name=business_name,
                        business_description=business_description,
                        country=CURRENCY_TO_COUNTRY[ss.currency],
                        reach_scope=reach_scope,
                    )
                ss.epicenters = to_epicenters(guess)
            else:
                ss.epicenters = []

            with st.spinner("Generating ad copy…"):
                copy = generate_ad_copy(
                    business_name=business_name,
                    business_description=business_description,
                    product_description=product_description,
                    currency=ss.currency,
                    destination=destination,
                    default_cta=cta_type,
                )
            ss.ad_copy = copy.model_dump()
            # Force the user-picked CTA to win over the LLM suggestion
            ss.ad_copy["call_to_action"] = cta_type

            # Interest targeting disabled by default — Meta's /search?type=adinterest
            # ranks by global audience size, which routinely returns wrong-country
            # matches (e.g. "Income tax" → "Australian Taxation Office") AND
            # surfaces deprecated interests that Meta then rejects at ad creation.
            #
            # For Lead Form ads with tight geo + age, broad targeting (no interests)
            # delivers as well or better. We keep the LLM-generated names in
            # ss.ad_copy for display only, then clear the field before YAML build
            # so flexible_spec is empty.
            #
            # TODO (post-pilot): rebuild interest resolution with country-biased
            # search + validation against Meta's /targetingvalidation endpoint
            # to filter deprecated IDs before they hit ad-creation.
            ss.ad_copy["interest_targeting"] = []

            # Upload each uploaded image to Meta /adimages to get its image_hash.
            # In Demo mode we use upload_mock (MD5 of file bytes — deterministic,
            # no API call). With Demo mode OFF, upload_live() POSTs to Meta and
            # needs META_ACCESS_TOKEN.
            by_aspect = _image_paths_by_aspect()
            use_mock_upload = ss.get("demo_mode", True)
            spinner_label = "Generating image hashes…" if use_mock_upload else "Uploading images to Meta…"

            image_hash = None
            image_hash_story = None
            image_hash_portrait = None

            with st.spinner(spinner_label):
                if "1:1" in by_aspect:
                    image_hash = _ensure_image_hash(
                        by_aspect["1:1"], client["ad_account_id"], use_mock_upload,
                    )
                if "9:16" in by_aspect:
                    image_hash_story = _ensure_image_hash(
                        by_aspect["9:16"], client["ad_account_id"], use_mock_upload,
                    )
                if "4:5" in by_aspect:
                    image_hash_portrait = _ensure_image_hash(
                        by_aspect["4:5"], client["ad_account_id"], use_mock_upload,
                    )

            if image_hash is None:
                # No 1:1 image uploaded — Meta requires at least one image_hash on
                # link_data. Use a placeholder and surface a warning so the user
                # knows the YAML can't be launched as-is.
                image_hash = "REPLACE_WITH_UPLOADED_HASH"
                st.warning(
                    "No 1:1 square image uploaded — `image_hash` is a placeholder. "
                    "Upload a Feed (square) image before launching."
                )

            yaml_dict = build_meta_yaml(
                client=client,
                currency=ss.currency,
                ad_copy=ss.ad_copy,
                epicenters=ss.epicenters,
                daily_budget=daily_budget,
                destination=destination,
                cta_type=cta_type,
                landing_page_url=website_url,
                lead_form_config=lead_form_config,
                image_hash=image_hash,
                image_hash_story=image_hash_story,
                image_hash_portrait=image_hash_portrait,
                bid_strategy=bidding,
                launch_status=ss.get("launch_status", "PAUSED"),
            )

            ss.rendered_yaml = yaml_dict
            ss.mock_output = ""

            ss.preview_data = {
                "destination": destination,
                "business_name": business_name,
                "website_url": website_url,
                "ad_copy": ss.ad_copy,
                "images": [v for v in ss.uploaded_files.values() if v["kind"] == "image"],
                "video": next((v for v in ss.uploaded_files.values() if v["kind"] == "video"), None),
                "lead_form": lead_form_config,
                "currency": ss.currency,
            }
        except Exception as e:
            import traceback
            st.error(f"Build failed: {type(e).__name__}: {e}")
            with st.expander("Full error trace (debugging)", expanded=True):
                st.code(traceback.format_exc(), language="text")


if btn_mock.button("Run mock", use_container_width=True, disabled=ss.rendered_yaml is None):
    try:
        from adapters import get_adapter  # type: ignore[import-not-found]
        from builders import build_all  # type: ignore[import-not-found]
        from validate import validate  # type: ignore[import-not-found]

        spec = validate(ss.rendered_yaml)
        operations = build_all(spec)
        buf = StringIO()
        adapter = get_adapter("mock", spec.ad_account_id)
        adapter.run(operations, stream=buf, spec=spec)
        ss.mock_output = buf.getvalue()
    except Exception as e:
        st.error(str(e))


# ---------- Launch to Meta (live) ----------
# Disabled until: a YAML is built AND Demo mode is OFF AND no placeholder image hash.
import os as _os  # local — only needed for the token check

_live_disabled_reason = None
if ss.rendered_yaml is None:
    _live_disabled_reason = "Click **Build YAML** first."
elif ss.get("demo_mode", True):
    _live_disabled_reason = "Turn **Demo mode** OFF (sidebar) — live launch needs real image hashes."
elif not _os.environ.get("META_ACCESS_TOKEN"):
    _live_disabled_reason = "META_ACCESS_TOKEN not configured."
else:
    img_hash = (ss.rendered_yaml.get("ad", {}).get("creative", {})
                .get("object_story_spec", {}).get("link_data", {})
                .get("image_hash", ""))
    if img_hash == "REPLACE_WITH_UPLOADED_HASH":
        _live_disabled_reason = "Image hash is a placeholder — re-upload your image with Demo OFF."

if btn_live.button(
    "Launch to Meta",
    use_container_width=True,
    type="primary" if not _live_disabled_reason else "secondary",
    disabled=bool(_live_disabled_reason),
):
    chosen = ss.get("launch_status", "PAUSED")
    if chosen == "ACTIVE":
        # ACTIVE means real spend begins. Require explicit confirmation.
        ss.confirm_active_launch = True
    else:
        # PAUSED launches without confirmation — no money moves yet.
        ss.launch_result = ""
        ss.launch_error = ""
        try:
            from adapters import get_adapter
            from builders import build_all
            from validate import validate

            spec = validate(ss.rendered_yaml)
            operations = build_all(spec)
            buf = StringIO()
            with st.spinner("Sending to Meta…"):
                adapter = get_adapter("meta", spec.ad_account_id)
                adapter.run(operations, stream=buf, spec=spec)
            ss.launch_result = buf.getvalue()
        except Exception as e:
            ss.launch_error = str(e)

if _live_disabled_reason and ss.rendered_yaml is not None:
    st.caption(f"_Launch button locked: {_live_disabled_reason}_")


# Confirmation dialog when launching ACTIVE — real money guard
if ss.confirm_active_launch:
    with st.container(border=True):
        st.warning(
            f"**Launch as ACTIVE on `act_{ss.rendered_yaml.get('ad_account_id', '')}`?**  \n"
            "Spending will begin within ~30 minutes. Daily budget = "
            f"{ss.rendered_yaml.get('ad_set', {}).get('daily_budget', 0) / 100:.2f} "
            f"(in minor units, divide by 100 for INR or USD)."
        )
        c1, c2 = st.columns(2)
        if c1.button("Yes, launch ACTIVE", type="primary"):
            ss.confirm_active_launch = False
            ss.launch_result = ""
            ss.launch_error = ""
            try:
                from adapters import get_adapter
                from builders import build_all
                from validate import validate

                spec = validate(ss.rendered_yaml)
                operations = build_all(spec)
                buf = StringIO()
                with st.spinner("Sending to Meta…"):
                    adapter = get_adapter("meta", spec.ad_account_id)
                    adapter.run(operations, stream=buf, spec=spec)
                ss.launch_result = buf.getvalue()
            except Exception as e:
                ss.launch_error = str(e)
            st.rerun()
        if c2.button("Cancel"):
            ss.confirm_active_launch = False
            st.rerun()


# Surface launch result / error
if ss.get("launch_result"):
    st.success("Live launch complete.")
    with st.expander("Launch output (real Meta API responses)", expanded=True):
        st.code(ss.launch_result, language="text")
if ss.get("launch_error"):
    st.error(f"Launch failed: {ss.launch_error}")


if ss.ad_copy:
    with st.expander("Generated copy + targeting", expanded=False):
        st.json(ss.ad_copy)

if ss.image_hash_cache:
    with st.expander("Image hashes", expanded=False):
        rows = [
            {
                "File": Path(path).name,
                "Mode": mode,
                "image_hash": h,
            }
            for (path, mode), h in ss.image_hash_cache.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

if ss.epicenters:
    with st.expander("Resolved cities", expanded=False):
        st.dataframe(ss.epicenters, use_container_width=True, hide_index=True)

if ss.rendered_yaml:
    with st.expander("YAML preview", expanded=False):
        yaml_text = yaml.safe_dump(ss.rendered_yaml, sort_keys=False, indent=2)
        st.code(yaml_text, language="yaml")
        st.download_button(
            "Download YAML",
            data=yaml_text,
            file_name=f"{(business_name or 'campaign').replace(' ', '_').lower()}.yaml",
            mime="text/yaml",
        )

if ss.mock_output:
    with st.expander("Mock launcher output", expanded=False):
        st.code(ss.mock_output, language="text")
