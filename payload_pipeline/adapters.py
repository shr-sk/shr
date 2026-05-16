"""Adapters that consume the operation list.

`MockAdapter` (default) — prints each operation as JSON, substitutes fake
resource IDs. No network call.

`MetaAdapter` — real Meta Marketing API adapter via raw HTTP (Graph API
is REST+JSON; no need for the heavy `facebook_business` SDK). Supports
`validate_only=True` to dry-run against Meta's validation without
creating anything.

Pilot guard: conversion objectives (OUTCOME_SALES, OUTCOME_LEADS) and
conversion optimization goals (OFFSITE_CONVERSIONS, VALUE, etc.) are
blocked unless CONVERSION_TRACKING_VERIFIED=true is set in env. Smart
delivery without Pixel + CAPI is blind.
"""
import json
import os
import sys
from typing import Any, TextIO


_PLACEHOLDERS = {
    "campaign": "${CAMPAIGN_ID}",
    "ad_set": "${AD_SET_ID}",
    "ad": "${AD_ID}",
}

_CONVERSION_OBJECTIVES = {"OUTCOME_SALES", "OUTCOME_LEADS"}
_CONVERSION_OPT_GOALS = {
    "OFFSITE_CONVERSIONS", "VALUE", "LEAD_GENERATION", "QUALITY_LEAD",
}


def _substitute(obj: Any, refs: dict[str, str]) -> Any:
    if isinstance(obj, str):
        return refs.get(obj, obj)
    if isinstance(obj, dict):
        return {k: _substitute(v, refs) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, refs) for v in obj]
    return obj


class MockAdapter:
    def __init__(self, ad_account_id: str):
        self.ad_account_id = ad_account_id

    def run(self, operations: list[dict], stream: TextIO | None = None,
            *, spec=None) -> None:
        out = stream or sys.stdout
        refs: dict[str, str] = {}
        out.write(f"=== MOCK RUN (no API calls) — ad_account=act_{self.ad_account_id} ===\n\n")

        # If spec carries a lead_form config, mock-create the form first so
        # the lead_gen_form_id placeholder gets substituted in later steps.
        if spec is not None and getattr(spec, "lead_form", None) is not None:
            from lead_form_create import MockFormAdapter
            page_id = spec.ad.creative.object_story_spec.page_id
            fallback_url = spec.ad.creative.object_story_spec.link_data.link
            out.write("--- Step 0: MOCK form create (POST /<page>/leadgen_forms) ---\n")
            fake_form_id = MockFormAdapter(page_id).create(
                spec.lead_form.model_dump(),
                fallback_thank_you_url=fallback_url,
            )
            out.write(f"  -> fake form_id: {fake_form_id}\n\n")
            refs["REPLACE_AFTER_LEAD_FORM_CREATED"] = fake_form_id

        for i, op in enumerate(operations, 1):
            payload = _substitute(op["payload"], refs)
            out.write(f"--- Step {i}: POST /{op['endpoint']} ---\n")
            out.write(json.dumps(payload, indent=2, default=str))
            out.write("\n")

            ref_key = op.get("ref_key")
            if ref_key in _PLACEHOLDERS:
                fake_id = str(1_000_000_000 + i)
                refs[_PLACEHOLDERS[ref_key]] = fake_id
                out.write(f"  -> assigned id: {fake_id}\n")
            out.write("\n")
        out.write("=== MOCK RUN COMPLETE — nothing was sent to Meta. ===\n")


class MetaAdapter:
    """Live Meta Marketing API adapter.

    Reads credentials from environment variables (load .env in launch.py):
      META_ACCESS_TOKEN     long-lived token from Events Manager or a system user
      META_API_VERSION      e.g. v19.0 (default)

    Also honoured:
      CONVERSION_TRACKING_VERIFIED  must be 'true' to use OUTCOME_SALES /
                                    OUTCOME_LEADS / OFFSITE_CONVERSIONS /
                                    VALUE / LEAD_GENERATION / QUALITY_LEAD.

    Status is forced to PAUSED by the builders — the human flips to ACTIVE
    in Ads Manager after review.
    """

    def __init__(self, ad_account_id: str, access_token: str | None = None,
                 validate_only: bool = False):
        self.ad_account_id = ad_account_id
        self.access_token = access_token or os.environ.get("META_ACCESS_TOKEN")
        self.api_version = os.environ.get("META_API_VERSION", "v19.0")
        self.validate_only = validate_only

    def run(self, operations: list[dict], stream: TextIO | None = None,
            *, spec=None) -> None:
        self._check_pilot_guard(operations)
        if not self.access_token:
            raise RuntimeError(
                "META_ACCESS_TOKEN not set in environment. "
                "Copy .env.example to .env and fill it in."
            )
        try:
            import requests  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "requests is not installed. Run:\n"
                "  cd payload_pipeline && .venv/bin/pip install -r meta/requirements.txt"
            ) from e

        out = stream or sys.stdout
        mode = "validate_only" if self.validate_only else "LIVE"
        out.write(f"=== META {mode} RUN — ad_account=act_{self.ad_account_id} ===\n\n")

        refs: dict[str, str] = {}

        # If the spec carries a lead_form config, create the form FIRST and
        # register its id so the placeholder in the ad creative gets substituted.
        if spec is not None and getattr(spec, "lead_form", None) is not None:
            page_id = spec.ad.creative.object_story_spec.page_id
            fallback_url = spec.ad.creative.object_story_spec.link_data.link
            if self.validate_only:
                # Meta validate_only won't accept a fake form_id either, so we
                # skip the actual form creation and use a placeholder. The
                # ad-creation step will fail validation downstream, but
                # campaign + ad_set will still be validated end-to-end.
                out.write(
                    "  (validate_only) — skipping real form creation; "
                    "ad-step will fail with 'invalid form_id' (expected).\n\n"
                )
                form_id = "VALIDATE_ONLY_PLACEHOLDER"
            else:
                from lead_form_create import LiveFormAdapter
                out.write("--- Step 0: POST /<page>/leadgen_forms (lead form create) ---\n")
                try:
                    form_id = LiveFormAdapter(page_id, self.access_token).create(
                        spec.lead_form.model_dump(),
                        fallback_thank_you_url=fallback_url,
                    )
                except Exception as e:
                    out.write(f"  -> FAILED: {type(e).__name__}: {e}\n")
                    raise
                out.write(f"  -> form_id: {form_id}\n\n")
            refs["REPLACE_AFTER_LEAD_FORM_CREATED"] = form_id

        for i, op in enumerate(operations, 1):
            payload = _substitute(op["payload"], refs)
            url = f"https://graph.facebook.com/{self.api_version}/{op['endpoint']}"
            out.write(f"--- Step {i}: POST /{op['endpoint']} ---\n")
            try:
                resource_id = self._post(url, payload)
            except Exception as e:
                out.write(f"  -> FAILED: {type(e).__name__}: {e}\n")
                raise
            out.write(f"  -> id: {resource_id or '(empty — validate_only success)'}\n")

            ref_key = op.get("ref_key")
            if ref_key in _PLACEHOLDERS and resource_id:
                refs[_PLACEHOLDERS[ref_key]] = resource_id
            elif ref_key in _PLACEHOLDERS and self.validate_only and not resource_id:
                # Meta's validate_only succeeds but returns no id, so we can't
                # validate later steps that reference this one. Stop here with a
                # clear message instead of cascading 'Invalid id' errors.
                out.write(
                    "\n  Stopping early: subsequent steps reference this id, but "
                    "validate_only mode doesn't return real ids. To validate the "
                    "full chain, use live mode (--adapter meta, no --validate-only). "
                    "It creates resources at status=PAUSED in your sandbox — safe.\n"
                )
                break

        out.write(f"\n=== {mode} RUN COMPLETE — "
                  f"{'nothing created' if self.validate_only else 'campaign at PAUSED'}. ===\n")

    def _post(self, url: str, body: dict) -> str:
        import requests
        params = {"access_token": self.access_token}
        if self.validate_only:
            # Meta accepts this as a JSON-string array in the query string.
            params["execution_options"] = json.dumps(["validate_only"])
        response = requests.post(url, json=body, params=params, timeout=30)
        if response.status_code != 200:
            detail = response.text
            try:
                err = response.json().get("error", {})
                detail = f"{err.get('type', '?')} ({err.get('code', '?')}): {err.get('message', response.text)}"
                if err.get("error_user_msg"):
                    detail += f" | user message: {err['error_user_msg']}"
            except Exception:
                pass
            raise RuntimeError(f"HTTP {response.status_code}: {detail}")
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise RuntimeError(f"non-JSON response: {response.text[:300]}")
        return data.get("id", "")  # may be empty in validate_only on some endpoints

    def _check_pilot_guard(self, operations: list[dict]) -> None:
        if os.environ.get("CONVERSION_TRACKING_VERIFIED", "").lower() == "true":
            return
        for op in operations:
            if op["resource_type"] == "campaign":
                obj = op["payload"].get("objective")
                if obj in _CONVERSION_OBJECTIVES:
                    raise RuntimeError(
                        f"Campaign objective '{obj}' requires Pixel + CAPI to be meaningful "
                        f"(smart delivery is blind without conversion data). For pilot, use "
                        f"OUTCOME_TRAFFIC. To override, set CONVERSION_TRACKING_VERIFIED=true."
                    )
            if op["resource_type"] == "ad_set":
                goal = op["payload"].get("optimization_goal")
                if goal in _CONVERSION_OPT_GOALS:
                    raise RuntimeError(
                        f"Optimization goal '{goal}' requires Pixel + CAPI. "
                        f"For pilot, use LINK_CLICKS or LANDING_PAGE_VIEWS. "
                        f"To override, set CONVERSION_TRACKING_VERIFIED=true."
                    )


def get_adapter(name: str, ad_account_id: str, access_token: str | None = None,
                validate_only: bool = False):
    if name == "mock":
        return MockAdapter(ad_account_id)
    if name == "meta":
        return MetaAdapter(ad_account_id, access_token, validate_only=validate_only)
    raise ValueError(f"unknown adapter: {name} (expected 'mock' or 'meta')")
