from __future__ import annotations

from pathlib import Path

import yaml

from .triggers import PREDICATES

REQUIRED_SECTIONS = ("triggers", "firmographics", "scoring", "urgency", "routing")


def load_rules(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        rules = yaml.safe_load(fh)
    if not isinstance(rules, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    missing = [s for s in REQUIRED_SECTIONS if s not in rules]
    if missing:
        raise ValueError(f"{path}: missing sections: {missing}")
    unknown = sorted(set(rules["triggers"]) - set(PREDICATES))
    if unknown:
        raise ValueError(f"{path}: no predicate implemented for triggers: {unknown}")
    return rules
