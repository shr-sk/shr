"""Create a Meta Instant Form (LeadGenForm) via the Marketing API.

The form must exist BEFORE the ad creative references it. Workflow:

  1. `MockFormAdapter` or `LiveFormAdapter` → `.create(config)` returns form_id
  2. Caller swaps that form_id into the ad's
     `call_to_action.value.lead_gen_form_id` field
  3. Ad creation proceeds with the real form_id

Used by `payload_pipeline/meta/adapters.py:LiveAdapter` automatically when
an operation set includes a `value_lead_gen_form_id` placeholder and the
spec carries a `lead_form` block.
"""
import hashlib
import json
import logging
import os
from typing import Any


log = logging.getLogger("meta_lead_form")


# Maps our prefilled-question keys to Meta's question `type` strings.
# Meta accepts `EMAIL`, `PHONE`, `FULL_NAME` etc. directly.
_PREFILLED_ALIASES = {
    "PHONE_NUMBER": "PHONE",
}


def _build_questions(config: dict) -> list[dict]:
    """Convert our config to Meta's `questions` array.

    Prefilled questions become `{type: <type>}` entries; custom ones become
    `{type: CUSTOM, label: ..., key: q1/q2/...}` short-answer entries.
    """
    out: list[dict] = []
    for key in config.get("prefilled_questions") or []:
        meta_type = _PREFILLED_ALIASES.get(key.upper(), key.upper())
        out.append({"type": meta_type})
    for i, q_text in enumerate(config.get("custom_questions") or [], 1):
        if not q_text or not str(q_text).strip():
            continue
        out.append({
            "type": "CUSTOM",
            "label": str(q_text).strip(),
            "key": f"q{i}",
        })
    return out


def _build_form_payload(config: dict, fallback_thank_you_url: str = "") -> dict:
    """Build the JSON body for `POST /page/{page_id}/leadgen_forms`."""
    thank_you_url = fallback_thank_you_url or "https://example.com"
    return {
        "name": config["name"],
        "questions": _build_questions(config),
        "privacy_policy": {
            "url": config["privacy_url"],
            "link_text": "Privacy Policy",
        },
        "thank_you_page": {
            "title": "Thanks!",
            "body": config.get("thank_you_message", "We'll be in touch shortly."),
            "button_text": "Visit website",
            "button_type": "VIEW_WEBSITE",
            "website_url": thank_you_url,
        },
        "locale": config.get("locale", "en_US"),
    }


class MockFormAdapter:
    """Prints what would be POSTed; returns a deterministic fake form_id."""

    def __init__(self, page_id: str):
        self.page_id = page_id

    def create(self, config: dict, fallback_thank_you_url: str = "") -> str:
        payload = _build_form_payload(config, fallback_thank_you_url)
        log.info(f"MOCK form create -> POST /{self.page_id}/leadgen_forms")
        log.info(f"  payload: {json.dumps(payload, default=str)[:400]}...")
        fake_id = "form_" + hashlib.md5(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:14]
        log.info(f"  -> fake form_id: {fake_id}")
        return fake_id


class LiveFormAdapter:
    """Real Meta API call to create the lead form.

    Requires `META_ACCESS_TOKEN` to include `pages_manage_ads` (or
    `pages_manage_leads`) permission on the Page that hosts the form.
    """

    def __init__(self, page_id: str, access_token: str | None = None):
        self.page_id = page_id
        self.access_token = access_token or os.environ.get("META_ACCESS_TOKEN")
        self.api_version = os.environ.get("META_API_VERSION", "v19.0")

    def create(self, config: dict, fallback_thank_you_url: str = "") -> str:
        if not self.access_token:
            raise RuntimeError(
                "META_ACCESS_TOKEN not set — needed to create lead forms."
            )
        try:
            import requests
        except ImportError as e:
            raise RuntimeError(
                "requests is not installed. Run: pip install -r requirements.txt"
            ) from e

        payload = _build_form_payload(config, fallback_thank_you_url)
        url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}/leadgen_forms"
        log.info(f"POST {url}")
        log.info(f"  payload: {json.dumps(payload, default=str)[:400]}...")
        r = requests.post(
            url,
            params={"access_token": self.access_token},
            json=payload,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(
                f"lead form create HTTP {r.status_code}: {_format_error(r)}"
            )
        form_id = r.json().get("id")
        if not form_id:
            raise RuntimeError(
                f"lead form create succeeded but no id in response: {r.text[:300]}"
            )
        log.info(f"  -> form_id: {form_id}")
        return form_id


def _format_error(response) -> str:
    try:
        err = response.json().get("error", {})
        out = (
            f"{err.get('type', '?')} ({err.get('code', '?')}): "
            f"{err.get('message', response.text[:200])}"
        )
        if err.get("error_user_msg"):
            out += f" | {err['error_user_msg']}"
        return out
    except Exception:
        return response.text[:300]


def get_form_adapter(name: str, page_id: str, access_token: str | None = None):
    if name == "mock":
        return MockFormAdapter(page_id)
    if name == "meta":
        return LiveFormAdapter(page_id, access_token)
    raise ValueError(f"unknown lead-form adapter: {name} (expected 'mock' or 'meta')")
