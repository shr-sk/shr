"""CLI entry point for the Meta Ads launcher.

Usage:
    # Mock — no API calls, no credentials needed.
    python launch.py inputs/example_traffic_campaign.yaml --adapter mock

    # Live but safe — calls Meta's API in validate_only mode.
    # Meta validates the payload but does NOT create anything.
    python launch.py inputs/example.yaml --adapter meta --validate-only

    # Live and creates campaign at status=PAUSED.
    python launch.py inputs/example.yaml --adapter meta
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Load .env BEFORE importing modules that read environment variables.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv only required for the meta adapter

from adapters import get_adapter
from builders import build_all
from validate import ValidationFailed, load_and_validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Launch a Meta Ads campaign from a YAML file (status=PAUSED)."
    )
    parser.add_argument("yaml_path", type=Path, help="Path to the campaign YAML.")
    parser.add_argument(
        "--adapter",
        choices=("mock", "meta"),
        default="mock",
        help="Which adapter to use. 'mock' (default) prints; 'meta' calls the real API.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="With --adapter meta, ask Meta to validate the payload but NOT create resources.",
    )
    args = parser.parse_args(argv)

    if not args.yaml_path.exists():
        print(f"error: file not found: {args.yaml_path}", file=sys.stderr)
        return 2

    try:
        spec = load_and_validate(args.yaml_path)
    except ValidationFailed as e:
        print(str(e), file=sys.stderr)
        return 1

    operations = build_all(spec)
    adapter = get_adapter(
        args.adapter,
        spec.ad_account_id,
        validate_only=args.validate_only,
    )
    # spec is passed so adapters can read auxiliary config (e.g. spec.lead_form
    # for Lead Form ads — adapter creates the form FIRST, then runs operations).
    adapter.run(operations, spec=spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
