from __future__ import annotations

from .enrichment import Enrichment
from .models import Account


def route(account: Account, trigger: str, enrichment: Enrichment, rules: dict) -> tuple[str, str]:
    """First matching rule wins. Returns (lane, reason)."""
    cfg = rules["routing"]

    if account.arr >= cfg["named_arr_threshold"]:
        return "named", (
            f"ARR {account.arr:,.0f} >= named threshold {cfg['named_arr_threshold']:,}"
        )

    if trigger == "cancellation_started":
        return "pooled", "save lane: cancellation routed to a person"

    skipped = enrichment.tags & set(cfg["skip_digital_for"])
    if skipped:
        return "pooled", f"skips digital lane ({', '.join(sorted(skipped))})"

    digital_first = rules["triggers"][trigger].get("digital_first", True)
    if not digital_first:
        return "pooled", f"{trigger} is not digital-first"

    max_touches = cfg["digital_max_touches"]
    if account.digital_touches < max_touches:
        return "digital", f"digital touch {account.digital_touches + 1} of {max_touches}"
    return "pooled", f"escalated after {account.digital_touches} unanswered digital touches"
