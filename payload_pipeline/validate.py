"""Load YAML and validate against the Pydantic schema.

Errors are reformatted into beginner-friendly messages.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import yaml
from pydantic import ValidationError

from schemas import MetaCampaignYaml


class ValidationFailed(Exception):
    def __init__(self, lines: list[str]):
        self.lines = lines
        super().__init__("\n".join(lines))


def load_yaml(path: Path) -> dict:
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValidationFailed([f"{path}: top-level YAML must be a mapping, got {type(data).__name__}"])
    return data


def validate(data: dict) -> MetaCampaignYaml:
    try:
        return MetaCampaignYaml.model_validate(data)
    except ValidationError as e:
        lines = [f"YAML validation failed with {e.error_count()} error(s):"]
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            lines.append(f"  - {loc}: {err['msg']}")
        raise ValidationFailed(lines) from e


def load_and_validate(path: Path) -> MetaCampaignYaml:
    return validate(load_yaml(path))
