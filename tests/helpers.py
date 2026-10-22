from pathlib import Path

from pooled_queue.config import load_rules
from pooled_queue.models import Account

ROOT = Path(__file__).resolve().parent.parent
RULES = load_rules(ROOT / "config/routing_rules.yaml")


def make_account(**overrides) -> Account:
    """A healthy account by default; override fields to trip a trigger."""
    base = dict(
        account_id="T1", name="Test Co", domain="test.example", arr=20000.0,
        seats_purchased=20, seats_active=18, lifetime_active_users=18,
        last_active_days=1, config_score=70, days_since_signup=300,
        days_to_renewal=200, cancellation_started=False, digital_touches=0,
    )
    base.update(overrides)
    return Account(**base)
