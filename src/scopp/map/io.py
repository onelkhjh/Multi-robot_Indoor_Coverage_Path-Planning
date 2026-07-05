"""Map file I/O."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from .models import MapDefinition
from .schema import MapValidationError, parse_map


def load_map(path: str | Path) -> MapDefinition:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
        data = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise MapValidationError(str(source), str(exc)) from exc
    if not isinstance(data, dict):
        raise MapValidationError("/", "document root must be an object")
    return parse_map(data)
