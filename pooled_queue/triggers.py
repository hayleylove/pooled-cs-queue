"""Trigger predicates. Thresholds come from the rules file, not from code."""
from __future__ import annotations

from typing import Callable

from .models import Account

Predicate = Callable[[Account, dict], bool]


def _cancellation_started(a: Account, p: dict) -> bool:
    return a.cancellation_started


def _renewal_approaching(a: Account, p: dict) -> bool:
    return a.days_to_renewal is not None and 0 <= a.days_to_renewal <= p["days_to_renewal_lte"]


def _solo_user_quiet(a: Account, p: dict) -> bool:
    return a.lifetime_active_users == 1 and a.last_active_days >= p["quiet_days_gte"]


def _stalled_onboarding(a: Account, p: dict) -> bool:
    in_window = p["min_days_since_signup"] <= a.days_since_signup <= p["max_days_since_signup"]
    # config_score > 0 keeps this distinct from nothing_configured
    return in_window and 0 < a.config_score < p["config_score_lt"]


def _nothing_configured(a: Account, p: dict) -> bool:
    return a.config_score == 0 and a.days_since_signup >= p["min_days_since_signup"]


def _seat_underuse(a: Account, p: dict) -> bool:
    return a.seats_purchased >= p["min_seats"] and a.utilization < p["utilization_lt"]


PREDICATES: dict[str, Predicate] = {
    "cancellation_started": _cancellation_started,
    "renewal_approaching": _renewal_approaching,
    "solo_user_quiet": _solo_user_quiet,
    "stalled_onboarding": _stalled_onboarding,
    "nothing_configured": _nothing_configured,
    "seat_underuse": _seat_underuse,
}


def fired_triggers(account: Account, rules: dict) -> list[str]:
    """Triggers that fire for an account, highest weight first."""
    fired = [
        name
        for name, spec in rules["triggers"].items()
        if PREDICATES[name](account, spec.get("params", {}))
    ]
    fired.sort(key=lambda name: -rules["triggers"][name]["weight"])
    return fired
