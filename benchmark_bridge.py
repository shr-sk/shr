"""Subprocess bridge into meta-insights-archive.

Same pattern as Google_Ads/benchmark_bridge.py — runs the CLI, parses JSON.
Cached at the call site (Streamlit `@st.cache_data(ttl=...)`).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

INSIGHTS_REPO = Path(__file__).resolve().parent.parent / "meta-insights-archive"


def _resolve_cli() -> list[str]:
    if not INSIGHTS_REPO.exists():
        raise RuntimeError(f"meta-insights-archive not found at {INSIGHTS_REPO}")
    # Use the existing venv's python for the subprocess
    venv_py = Path(__file__).resolve().parent.parent / "payload_pipeline" / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else "python"
    return [py, "-m", "cli"]


def run_benchmark(
    *,
    ad_account_id: str,
    adapter: str = "mock",
    lookback_days: int = 30,
) -> dict:
    """Run meta-insights-archive and parse its JSON output."""
    argv = _resolve_cli() + [
        "--adapter", adapter,
        "--ad-account-id", ad_account_id,
        "--lookback-days", str(lookback_days),
    ]
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        cwd=str(INSIGHTS_REPO),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"meta-insights-archive exited {proc.returncode}\nstderr:\n{proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"meta-insights-archive stdout not JSON: {e}\nfirst 500 chars:\n{proc.stdout[:500]}"
        ) from e


def summary_lines(report: dict) -> list[str]:
    """Pull the headline numbers into a one-line-per-account list."""
    lines: list[str] = []
    health = report.get("health", {})
    score = health.get("score")
    totals = report.get("account_totals", {})
    spend = totals.get("spend")
    impressions = totals.get("impressions")
    flags = health.get("flags") or []

    bits = [f"**health {score}/100**" if score is not None else ""]
    if spend is not None:
        bits.append(f"spend {spend:,.2f}")
    if impressions is not None:
        bits.append(f"{impressions:,} impressions")
    if flags:
        bits.append("flags: " + ", ".join(flags))
    lines.append(" · ".join(b for b in bits if b))
    return lines
