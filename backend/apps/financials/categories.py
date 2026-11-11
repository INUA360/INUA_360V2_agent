"""Categorization rules loaded from config (never hard-coded in parser code)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "categories.yaml"


@lru_cache(maxsize=1)
def load_categories() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle)
    return data


def classify(details: str, direction: str) -> str:
    """Return a coarse category key. Unknown text is `uncategorized`."""
    text = (details or "").lower()
    for rule in load_categories().get("categories", []):
        expected_direction = rule.get("direction")
        if expected_direction and expected_direction != direction:
            continue
        if any(keyword.lower() in text for keyword in rule.get("keywords", [])):
            return str(rule["key"])
    return "uncategorized"


def category_label(key: str) -> str:
    for rule in load_categories().get("categories", []):
        if rule["key"] == key:
            return str(rule["label"])
    return "Uncategorized"
