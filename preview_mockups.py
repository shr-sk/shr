"""HTML/CSS mockups of how the ad will look on Facebook + Instagram surfaces.

Not pixel-perfect — Meta rerenders dynamically. These are demo-quality
representations using the user's uploaded media + Gemini-generated copy.
"""
from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from typing import Any


# Placeholder SVG — pale-blue 1:1 block with "Ad image" text
_PLACEHOLDER = (
    'data:image/svg+xml;base64,'
    'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MDAgNjAwIj48cmVjdC'
    'B3aWR0aD0iNjAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iI2UzZjJmZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmaWxs'
    'PSIjMTg3N2YyIiBmb250LWZhbWlseT0iSGVsdmV0aWNhLEFyaWFsIiBmb250LXNpemU9IjQ4cHgiIHRleHQtYW5jaG'
    '9yPSJtaWRkbGUiIGR5PSIuM2VtIj5BZCBpbWFnZTwvdGV4dD48L3N2Zz4='
)


def _img_uri(local_path: str | None) -> str:
    if not local_path:
        return _PLACEHOLDER
    p = Path(local_path)
    if not p.exists():
        return _PLACEHOLDER
    mime = mimetypes.guess_type(str(p))[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def _e(s: str | None) -> str:
    return html.escape(s or "")


def _pick(images: list[dict], aspect: str) -> str:
    if not images:
        return _PLACEHOLDER
    for img in images:
        if img.get("aspect") == aspect:
            return _img_uri(img.get("local_path"))
    return _img_uri(images[0].get("local_path"))


def _cta_text(raw: str | None) -> str:
    if not raw:
        return "Learn More"
    return raw.replace("_", " ").title()


_CSS = """
<style>
.fbm-wrap{font-family:'Helvetica Neue',Arial,sans-serif;color:#1c1e21;background:#f0f2f5;padding:18px;border-radius:8px;display:flex;justify-content:center}
.fbm-card{background:#fff;border-radius:8px;overflow:hidden;border:1px solid #dadde1}
.fbm-cta{background:#e7f3ff;color:#1877f2;border:1px solid #1877f2;font-weight:600;padding:6px 12px;font-size:13px;border-radius:6px;cursor:pointer}
.fbm-pill{display:inline-block;font-size:11px;color:#65676b;font-weight:500}
.ig-cta{background:#fff;color:#000;border:1px solid #dbdbdb;font-weight:600;padding:6px 12px;font-size:13px;border-radius:8px;cursor:pointer;width:100%}
.ig-username{font-size:14px;font-weight:600;color:#000}
</style>
"""


# ============================================================================
# Facebook Feed
# ============================================================================

def fb_feed_mockup(d: dict[str, Any]) -> str:
    copy = d.get("ad_copy") or {}
    img = _pick(d.get("images") or [], "1:1")
    initials = (d.get("business_name") or "B")[0]
    return f"""{_CSS}
<div class="fbm-wrap">
  <div class="fbm-card" style="width:520px">
    <div style="padding:12px 14px;display:flex;gap:10px;align-items:center">
      <div style="width:40px;height:40px;border-radius:50%;background:#1877f2;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600">{_e(initials)}</div>
      <div style="flex:1">
        <div style="font-weight:600;font-size:15px">{_e(d.get('business_name'))}</div>
        <div class="fbm-pill">Sponsored · <span style="color:#65676b">🌐</span></div>
      </div>
      <div style="color:#65676b;font-size:20px">⋯</div>
    </div>
    <div style="padding:0 14px 12px;font-size:15px;line-height:1.4;color:#050505;white-space:pre-wrap">{_e(copy.get('primary_text'))}</div>
    <img src="{img}" style="width:100%;display:block">
    <div style="background:#f0f2f5;padding:12px 14px;display:flex;justify-content:space-between;align-items:center">
      <div style="min-width:0;flex:1;padding-right:12px">
        <div class="fbm-pill" style="text-transform:uppercase">{_e((d.get('website_url') or '').replace('https://','').replace('http://',''))}</div>
        <div style="font-weight:600;font-size:16px;color:#050505;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{_e(copy.get('headline'))}</div>
        {f'<div style="font-size:13px;color:#65676b;margin-top:1px">{_e(copy.get("description"))}</div>' if copy.get('description') else ''}
      </div>
      <button class="fbm-cta">{_e(_cta_text(copy.get('call_to_action')))}</button>
    </div>
    <div style="border-top:1px solid #ced0d4;padding:6px 14px;display:flex;justify-content:space-around;color:#65676b;font-size:14px">
      <span>👍 Like</span><span>💬 Comment</span><span>↗ Share</span>
    </div>
  </div>
</div>
"""


# ============================================================================
# Instagram Feed
# ============================================================================

def ig_feed_mockup(d: dict[str, Any]) -> str:
    copy = d.get("ad_copy") or {}
    img = _pick(d.get("images") or [], "4:5") or _pick(d.get("images") or [], "1:1")
    initials = (d.get("business_name") or "B")[0]
    handle = (d.get("business_name") or "brand").lower().replace(" ", "").replace("&", "_")[:24]
    return f"""{_CSS}
<div class="fbm-wrap" style="background:#fafafa">
  <div style="width:380px;background:#fff;border:1px solid #dbdbdb;border-radius:4px">
    <div style="padding:10px 14px;display:flex;gap:10px;align-items:center">
      <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);padding:2px">
        <div style="width:100%;height:100%;border-radius:50%;background:#1877f2;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600">{_e(initials)}</div>
      </div>
      <div style="flex:1">
        <div class="ig-username">{_e(handle)}</div>
        <div style="font-size:12px;color:#737373">Sponsored</div>
      </div>
      <div style="font-size:18px;color:#000">⋯</div>
    </div>
    <img src="{img}" style="width:100%;aspect-ratio:4/5;object-fit:cover;display:block">
    <div style="padding:8px 14px">
      <div style="display:flex;justify-content:space-between;font-size:22px;color:#000;margin-bottom:6px">
        <span>♡  💬  ↗</span><span>🔖</span>
      </div>
      <div style="font-size:13px;line-height:1.4">
        <span style="font-weight:600">{_e(handle)}</span> {_e(copy.get('primary_text'))}
      </div>
    </div>
    <div style="padding:8px 14px 12px">
      <button class="ig-cta">{_e(_cta_text(copy.get('call_to_action')))}</button>
    </div>
  </div>
</div>
"""


# ============================================================================
# Stories / Reels (9:16)
# ============================================================================

def stories_mockup(d: dict[str, Any], surface_label: str = "Stories") -> str:
    copy = d.get("ad_copy") or {}
    img = _pick(d.get("images") or [], "9:16") or _pick(d.get("images") or [], "1:1")
    initials = (d.get("business_name") or "B")[0]
    return f"""{_CSS}
<div class="fbm-wrap" style="background:#000">
  <div style="width:270px;height:480px;position:relative;border-radius:14px;overflow:hidden;background:url('{img}') center/cover #222">
    <div style="position:absolute;top:0;left:0;right:0;height:3px;display:flex;gap:2px;padding:8px">
      <div style="flex:1;background:rgba(255,255,255,.4);height:2px;border-radius:1px"><div style="height:100%;width:35%;background:#fff;border-radius:1px"></div></div>
    </div>
    <div style="position:absolute;top:24px;left:14px;right:14px;display:flex;gap:8px;align-items:center;color:#fff">
      <div style="width:30px;height:30px;border-radius:50%;background:#1877f2;border:2px solid #fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:13px">{_e(initials)}</div>
      <div style="flex:1">
        <div style="font-size:13px;font-weight:600">{_e(d.get('business_name'))}</div>
        <div style="font-size:11px;opacity:.85">Sponsored</div>
      </div>
      <div style="font-size:18px">×</div>
    </div>
    <div style="position:absolute;bottom:60px;left:14px;right:14px;color:#fff;text-shadow:0 1px 6px rgba(0,0,0,.6)">
      <div style="font-size:15px;font-weight:600;line-height:1.3">{_e(copy.get('headline'))}</div>
    </div>
    <div style="position:absolute;bottom:14px;left:14px;right:14px">
      <button style="width:100%;background:#fff;color:#000;border:none;padding:8px;border-radius:8px;font-weight:600;font-size:13px">{_e(_cta_text(copy.get('call_to_action')))} ↗</button>
    </div>
  </div>
</div>
"""


def reels_mockup(d: dict[str, Any]) -> str:
    return stories_mockup(d, surface_label="Reels")


# ============================================================================
# Facebook Right Column (1.91:1)
# ============================================================================

def fb_right_column_mockup(d: dict[str, Any]) -> str:
    copy = d.get("ad_copy") or {}
    img = _pick(d.get("images") or [], "1.91:1") or _pick(d.get("images") or [], "1:1")
    return f"""{_CSS}
<div class="fbm-wrap">
  <div class="fbm-card" style="width:280px">
    <img src="{img}" style="width:100%;aspect-ratio:1.91/1;object-fit:cover;display:block">
    <div style="padding:10px 12px">
      <div style="font-size:13px;font-weight:600;color:#050505;line-height:1.3">{_e(copy.get('headline'))}</div>
      <div class="fbm-pill" style="margin-top:4px">{_e((d.get('website_url') or '').replace('https://',''))}</div>
      <div style="font-size:12px;color:#65676b;margin-top:4px;line-height:1.4">{_e(copy.get('description') or '')}</div>
      <div class="fbm-pill" style="margin-top:6px">Sponsored</div>
    </div>
  </div>
</div>
"""


# ============================================================================
# Lead Form — Instant Form preview
# ============================================================================

def instant_form_preview(d: dict[str, Any]) -> str:
    """The form that opens AFTER the user taps the CTA on a Lead Form ad."""
    copy = d.get("ad_copy") or {}
    lf = d.get("lead_form") or {}
    img = _pick(d.get("images") or [], "1.91:1") or _pick(d.get("images") or [], "1:1")
    questions = lf.get("prefilled_questions") or ["FULL_NAME", "EMAIL", "PHONE_NUMBER"]
    field_labels = {
        "FULL_NAME": "Full name",
        "FIRST_NAME": "First name",
        "LAST_NAME": "Last name",
        "EMAIL": "Email address",
        "PHONE": "Phone number",
        "PHONE_NUMBER": "Phone number",
        "CITY": "City",
        "STATE": "State",
        "COUNTRY": "Country",
        "POST_CODE": "Postal code",
        "GENDER": "Gender",
        "DOB": "Date of birth",
    }
    rows_html = ""
    for q in questions:
        label = field_labels.get(q, q.title())
        rows_html += f"""
          <div style="margin-bottom:14px">
            <div style="font-size:13px;color:#65676b;font-weight:500;margin-bottom:4px">{_e(label)}</div>
            <div style="border:1px solid #dadde1;border-radius:6px;padding:10px;font-size:14px;color:#1c1e21;background:#f5f6f7">(prefilled from profile)</div>
          </div>
        """
    name = lf.get("name") or f"{d.get('business_name')} — Lead form"
    thank_you = lf.get("thank_you_message") or "Thanks! We'll be in touch shortly."

    return f"""{_CSS}
<div class="fbm-wrap" style="background:#f0f2f5">
  <div style="width:380px;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #dadde1">
    <div style="padding:10px 14px;border-bottom:1px solid #dadde1;display:flex;align-items:center;gap:10px;background:#fff">
      <div style="font-size:18px;color:#65676b">←</div>
      <div style="flex:1;font-size:14px;font-weight:600">{_e(d.get('business_name'))}</div>
      <div style="font-size:18px;color:#65676b">×</div>
    </div>
    <img src="{img}" style="width:100%;aspect-ratio:1.91/1;object-fit:cover;display:block">
    <div style="padding:18px">
      <div style="font-size:18px;font-weight:700;color:#1c1e21;line-height:1.3">{_e(copy.get('headline'))}</div>
      <div style="font-size:14px;color:#65676b;margin-top:6px;line-height:1.4">{_e(copy.get('primary_text'))}</div>
      <div style="margin-top:20px;font-size:12px;color:#65676b;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Contact details</div>
      <div style="margin-top:10px">{rows_html}</div>
      <button style="width:100%;background:#1877f2;color:#fff;border:none;padding:12px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer">Submit</button>
      <div style="font-size:11px;color:#65676b;margin-top:12px;line-height:1.4">By tapping Submit, you agree to send your info to {_e(d.get('business_name'))} who agrees to use it according to their privacy policy. Facebook will also use it subject to our Data Policy.</div>
    </div>
    <div style="background:#f0f2f5;padding:14px;text-align:center;border-top:1px solid #dadde1;color:#65676b;font-size:12px">
      After submit: <strong style="color:#1c1e21">"{_e(thank_you)}"</strong>
    </div>
  </div>
</div>
"""


# ============================================================================
# Per-destination surface lists
# ============================================================================

CHANNEL_SURFACES_WEBSITE = [
    ("Facebook Feed",            fb_feed_mockup),
    ("Instagram Feed",           ig_feed_mockup),
    ("Instagram Stories",        stories_mockup),
    ("Instagram Reels",          reels_mockup),
    ("Facebook Right Column",    fb_right_column_mockup),
]

CHANNEL_SURFACES_LEAD_FORM = [
    ("Facebook Feed (ad surface)",   fb_feed_mockup),
    ("Instagram Feed (ad surface)",  ig_feed_mockup),
    ("Instagram Stories",            stories_mockup),
    ("Instant Form (after tap)",     instant_form_preview),
]


def surfaces_for(destination: str) -> list[tuple[str, callable]]:
    if (destination or "").strip().lower().startswith("lead"):
        return CHANNEL_SURFACES_LEAD_FORM
    return CHANNEL_SURFACES_WEBSITE
