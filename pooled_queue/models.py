from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Account:
    account_id: str
    name: str
    domain: str
    arr: float
    seats_purchased: int
    seats_active: int
    lifetime_active_users: int
    last_active_days: int
    config_score: int            # 0-100 configuration maturity score
    days_since_signup: int
    days_to_renewal: int | None  # None when there is no renewal date
    cancellation_started: bool
    digital_touches: int         # automated touches sent without a response

    @property
    def utilization(self) -> float:
        if self.seats_purchased <= 0:
            return 0.0
        return self.seats_active / self.seats_purchased


@dataclass(frozen=True)
class Case:
    account_id: str
    account_name: str
    primary_trigger: str
    also_fired: tuple[str, ...]
    lane: str
    lane_reason: str
    score: float
    explain: str
    first_response_hours: int
    resolution_hours: int


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def load_accounts(path: str | Path) -> list[Account]:
    accounts: list[Account] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            renewal = row["days_to_renewal"].strip()
            accounts.append(
                Account(
                    account_id=row["account_id"].strip(),
                    name=row["name"].strip(),
                    domain=row["domain"].strip(),
                    arr=float(row["arr"]),
                    seats_purchased=int(row["seats_purchased"]),
                    seats_active=int(row["seats_active"]),
                    lifetime_active_users=int(row["lifetime_active_users"]),
                    last_active_days=int(row["last_active_days"]),
                    config_score=int(row["config_score"]),
                    days_since_signup=int(row["days_since_signup"]),
                    days_to_renewal=int(renewal) if renewal else None,
                    cancellation_started=_as_bool(row["cancellation_started"]),
                    digital_touches=int(row["digital_touches"]),
                )
            )
    return accounts
