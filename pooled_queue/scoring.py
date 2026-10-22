from __future__ import annotations

from .enrichment import Enrichment
from .models import Account


def firmographic_multiplier(enrichment: Enrichment, rules: dict) -> tuple[float, str]:
    """Largest applicable multiplier (no stacking), capped. Returns (value, label)."""
    firm = rules["firmographics"]
    candidates: list[tuple[str, float]] = []
    rank = enrichment.fortune_rank
    if rank is not None:
        if rank <= 100:
            candidates.append(("fortune500_top100", firm["fortune500"]["top100_multiplier"]))
        elif rank <= 500:
            candidates.append(("fortune500", firm["fortune500"]["top500_multiplier"]))
    if enrichment.priority_tier:
        tier_value = firm["priority_tiers"].get(enrichment.priority_tier, 1.0)
        candidates.append((f"priority:{enrichment.priority_tier}", tier_value))
    if not candidates:
        return 1.0, "none"
    label, value = max(candidates, key=lambda c: c[1])
    return min(value, firm["multiplier_cap"]), label


def score_case(
    account: Account, trigger: str, enrichment: Enrichment, rules: dict
) -> tuple[float, str]:
    weight = rules["triggers"][trigger]["weight"]
    multiplier, label = firmographic_multiplier(enrichment, rules)

    scoring = rules["scoring"]
    arr_bonus = min(account.arr / scoring["arr_per_point"], scoring["arr_bonus_max"])

    urgency = rules["urgency"]
    renewal_bonus = 0.0
    if (
        account.days_to_renewal is not None
        and 0 <= account.days_to_renewal <= urgency["renewal_within_days"]
    ):
        renewal_bonus = float(urgency["bonus_points"])

    total = round(weight * multiplier + arr_bonus + renewal_bonus, 1)
    explain = (
        f"{trigger} {weight} x{multiplier:g} [{label}] "
        f"+ arr {arr_bonus:.1f} + renewal {renewal_bonus:g} = {total}"
    )
    return total, explain
