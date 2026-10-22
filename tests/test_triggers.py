import unittest

from pooled_queue.triggers import fired_triggers
from .helpers import RULES, make_account


class TriggerTests(unittest.TestCase):
    def fired(self, **kw):
        return fired_triggers(make_account(**kw), RULES)

    def test_healthy_account_fires_nothing(self):
        self.assertEqual(self.fired(), [])

    def test_renewal_boundary_is_inclusive(self):
        self.assertIn("renewal_approaching", self.fired(days_to_renewal=60))
        self.assertNotIn("renewal_approaching", self.fired(days_to_renewal=61))

    def test_missing_renewal_date_does_not_fire(self):
        self.assertNotIn("renewal_approaching", self.fired(days_to_renewal=None))

    def test_stalled_and_nothing_configured_are_exclusive(self):
        zero = self.fired(config_score=0, days_since_signup=30)
        low = self.fired(config_score=10, days_since_signup=30)
        self.assertIn("nothing_configured", zero)
        self.assertNotIn("stalled_onboarding", zero)
        self.assertIn("stalled_onboarding", low)
        self.assertNotIn("nothing_configured", low)

    def test_solo_user_needs_exactly_one_lifetime_user(self):
        self.assertIn("solo_user_quiet", self.fired(lifetime_active_users=1, last_active_days=14))
        self.assertNotIn("solo_user_quiet", self.fired(lifetime_active_users=2, last_active_days=30))

    def test_seat_underuse_ignores_tiny_accounts(self):
        self.assertNotIn("seat_underuse", self.fired(seats_purchased=4, seats_active=0))
        self.assertIn("seat_underuse", self.fired(seats_purchased=10, seats_active=4))

    def test_highest_weight_trigger_comes_first(self):
        fired = self.fired(cancellation_started=True, days_to_renewal=10)
        self.assertEqual(fired[0], "cancellation_started")
