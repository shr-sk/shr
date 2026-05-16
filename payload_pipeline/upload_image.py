"""Upload an image to Meta's /adimages endpoint to get an image_hash.

Meta link-ads require a `creative.object_story_spec.link_data.image_hash`
that comes from a prior upload — you can't pass a local path directly.
This CLI does that upload and returns the hash so you can paste it into
the launcher YAML.

Usage:
    # Mock — no upload, prints a deterministic fake hash (MD5 of the file).
    # No credentials needed. Useful for verifying YAML wiring before going live.
    python upload_image.py /path/to/poster.jpg --ad-account-id 1234567890

    # Live — uploads to Meta and returns the real hash.
    python upload_image.py /path/to/poster.jpg --ad-account-id 1234567890 --adapter meta

The image_hash goes into your YAML at:
    ad.creative.object_story_spec.link_data.image_hash
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


def upload_mock(image_path: Path, ad_account_id: str) -> dict:
    """Deterministic MD5-of-file hash. Same shape as a real Meta image_hash."""
    fake_hash = hashlib.md5(image_path.read_bytes()).hexdigest()
    return {
        "mode": "mock",
        "image_hash": fake_hash,
        "filename": image_path.name,
        "size_bytes": image_path.stat().st_size,
        "ad_account_id": ad_account_id,
        "preview_url": None,
    }


def upload_live(image_path: Path, ad_account_id: str) -> dict:
    access_token = os.environ.get("META_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError(
            "META_ACCESS_TOKEN not set. Copy .env.example to .env and fill it in."
        )
    try:
        import requests
    except ImportError as e:
        raise RuntimeError(
            "requests is not installed. Run:\n"
            "  cd payload_pipeline && .venv/bin/pip install -r meta/requirements.txt"
        ) from e

    api_version = os.environ.get("META_API_VERSION", "v19.0")
    url = f"https://graph.facebook.com/{api_version}/act_{ad_account_id}/adimages"

    with image_path.open("rb") as f:
        files = {image_path.name: f}
        params = {"access_token": access_token}
        response = requests.post(url, files=files, params=params, timeout=60)

    if response.status_code != 200:
        detail = response.text
        try:
            err = response.json().get("error", {})
            detail = f"{err.get('type', '?')} ({err.get('code', '?')}): {err.get('message', detail)}"
            if err.get("error_user_msg"):
                detail += f" | {err['error_user_msg']}"
        except Exception:
            pass
        raise RuntimeError(f"HTTP {response.status_code}: {detail}")

    data = response.json()
    images = data.get("images", {})
    if not images:
        raise RuntimeError(f"unexpected response, no images key: {data}")

    # Response is keyed by filename; usually one entry. Pick the first.
    image_info = next(iter(images.values()))
    return {
        "mode": "live",
        "image_hash": image_info.get("hash"),
        "filename": image_path.name,
        "size_bytes": image_path.stat().st_size,
        "ad_account_id": ad_account_id,
        "preview_url": image_info.get("url"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload an image to Meta /adimages to get an image_hash."
    )
    parser.add_argument("image", type=Path, help="Path to local image file (jpg, png).")
    parser.add_argument(
        "--ad-account-id",
        default=os.environ.get("META_AD_ACCOUNT_ID"),
        help="Digits only, no act_ prefix. Defaults to META_AD_ACCOUNT_ID env var.",
    )
    parser.add_argument(
        "--adapter",
        choices=("mock", "meta"),
        default="mock",
        help="'mock' (default) returns deterministic fake hash; 'meta' uploads for real.",
    )
    args = parser.parse_args(argv)

    if not args.image.exists():
        print(f"error: file not found: {args.image}", file=sys.stderr)
        return 2

    if not args.ad_account_id:
        print("error: --ad-account-id is required (or set META_AD_ACCOUNT_ID in .env)", file=sys.stderr)
        return 2

    size_mb = args.image.stat().st_size / 1_048_576
    if size_mb > 30:
        print(f"warning: file is {size_mb:.1f} MB — Meta limit is ~30 MB", file=sys.stderr)

    try:
        if args.adapter == "mock":
            result = upload_mock(args.image, args.ad_account_id)
        else:
            result = upload_live(args.image, args.ad_account_id)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    # Human summary on stderr.
    print(f"✓ {result['mode']} upload OK", file=sys.stderr)
    print(f"  file:       {result['filename']} ({result['size_bytes'] / 1024:.1f} KB)", file=sys.stderr)
    print(f"  ad_account: act_{result['ad_account_id']}", file=sys.stderr)
    print(f"  image_hash: {result['image_hash']}", file=sys.stderr)
    if result.get("preview_url"):
        print(f"  preview:    {result['preview_url']}", file=sys.stderr)
    print(f"\nPaste into your YAML at  ad.creative.object_story_spec.link_data.image_hash",
          file=sys.stderr)

    # Machine-readable JSON on stdout (for scripting).
    print(json.dumps({
        "image_hash": result["image_hash"],
        "preview_url": result.get("preview_url"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
