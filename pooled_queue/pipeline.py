from __future__ import annotations

from .enrichment import Enricher
from .models import Account, Case
from .routing import route
from .scoring import score_case
from .triggers import fired_triggers


def build_queue(accounts: list[Account], enricher: Enricher, rules: dict) -> list[Case]:
    """One case per account (its highest-weight trigger), sorted by score."""
    cases: list[Case] = []
    for account in accounts:
        fired = fired_triggers(account, rules)
        if not fired:
            continue
        primary = fired[0]
        enrichment = enricher.lookup(account)
        score, explain = score_case(account, primary, enrichment, rules)
        lane, reason = route(account, primary, enrichment, rules)
        spec = rules["triggers"][primary]
        cases.append(
            Case(
                account_id=account.account_id,
                account_name=account.name,
                primary_trigger=primary,
                also_fired=tuple(fired[1:]),
                lane=lane,
                lane_reason=reason,
                score=score,
                explain=explain,
                first_response_hours=spec["first_response_hours"],
                resolution_hours=spec["resolution_hours"],
            )
        )
    cases.sort(key=lambda c: (-c.score, c.account_id))
    return cases
