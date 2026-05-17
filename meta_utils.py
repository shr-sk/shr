"""Helpers that touch Meta Graph API but aren't tied to launching campaigns.

Used by the dashboard to enrich Gemini-generated copy with real Meta IDs
before handing it to the launcher.
"""
from __future__ import annotations

import os
from typing import Any


def resolve_interest_ids(
    names: list[str],
    *,
    max_results: int = 5,
    timeout_s: int = 8,
) -> list[dict[str, Any]]:
    """Look up real Meta interest IDs for a list of free-text names.

    Returns a list of `{"id": "1234567", "name": "Income tax"}` dicts ready to
    drop into `flexible_spec.interests`.

    Returns an empty list when:
      - `META_ACCESS_TOKEN` is not set (e.g. demo mode)
      - The HTTP call fails or rate-limits
      - None of the names match anything in Meta's targeting catalog

    Caller should treat an empty result as "use broad targeting" rather than
    failing — Meta delivers fine without explicit interests when the audience
    is shaped by geo + age + Lead Form context.
    """
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token or not names:
        return []

    try:
        import requests  # type: ignore[import-not-found]
    except ImportError:
        return []

    api_ver = os.environ.get("META_API_VERSION", "v20.0")
    out: list[dict] = []
    seen_ids: set[str] = set()

    for raw_name in names[:max_results]:
        name = str(raw_name).strip()
        if not name:
            continue
        try:
            response = requests.get(
                f"https://graph.facebook.com/{api_ver}/search",
                params={
                    "type": "adinterest",
                    "q": name,
                    "limit": 1,
                    "access_token": token,
                },
                timeout=timeout_s,
            )
            if not response.ok:
                continue
            data = response.json().get("data", []) or []
            for item in data[:1]:
                iid = str(item.get("id") or "").strip()
                if not iid or iid in seen_ids:
                    continue
                seen_ids.add(iid)
                out.append({"id": iid, "name": item.get("name", name)})
        except Exception:
            # Any network / parse error → skip this name, keep going for the rest.
            continue

    return out
