import copy
import unittest

from pooled_queue.enrichment import Enrichment
from pooled_queue.routing import route
from pooled_queue.scoring import firmographic_multiplier, score_case
from .helpers import RULES, make_account

NONE = Enrichment()
TOP100 = Enrichment(fortune_rank=12)
MID = Enrichment(fortune_rank=300)


class ScoringTests(unittest.TestCase):
    def test_fortune_top100_outscores_identical_unranked_account(self):
        acct = make_account()
        base, _ = score_case(acct, "renewal_approaching", NONE, RULES)
        boosted, _ = score_case(acct, "renewal_approaching", TOP100, RULES)
        self.assertGreater(boosted, base)

    def test_rank_bands(self):
        self.assertEqual(firmographic_multiplier(TOP100, RULES)[0], 1.5)
        self.assertEqual(firmographic_multiplier(MID, RULES)[0], 1.25)
        self.assertEqual(firmographic_multiplier(Enrichment(fortune_rank=501), RULES)[0], 1.0)

    def test_multipliers_do_not_stack_and_respect_cap(self):
        both = Enrichment(fortune_rank=5, priority_tier="strategic")
        value, label = firmographic_multiplier(both, RULES)
        self.assertEqual((value, label), (1.6, "priority:strategic"))
        rules = copy.deepcopy(RULES)
        rules["firmographics"]["priority_tiers"]["strategic"] = 9.0
        self.assertEqual(firmographic_multiplier(both, rules)[0], 1.75)

    def test_arr_bonus_is_capped(self):
        huge = make_account(arr=10_000_000.0)
        score, _ = score_case(huge, "seat_underuse", NONE, RULES)
        self.assertEqual(score, 35 + 10)

    def test_renewal_urgency_applies_within_window_only(self):
        near, _ = score_case(make_account(days_to_renewal=30), "seat_underuse", NONE, RULES)
        far, _ = score_case(make_account(days_to_renewal=31), "seat_underuse", NONE, RULES)
        self.assertEqual(round(near - far, 1), 15.0)


class RoutingTests(unittest.TestCase):
    def test_large_arr_goes_named(self):
        lane, _ = route(make_account(arr=100_000.0), "seat_underuse", NONE, RULES)
        self.assertEqual(lane, "named")

    def test_cancellation_goes_to_a_person(self):
        lane, reason = route(make_account(), "cancellation_started", NONE, RULES)
        self.assertEqual(lane, "pooled")
        self.assertIn("save lane", reason)

    def test_top100_skips_digital(self):
        lane, _ = route(make_account(), "seat_underuse", TOP100, RULES)
        self.assertEqual(lane, "pooled")

    def test_mid_fortune_account_still_starts_digital(self):
        lane, _ = route(make_account(), "seat_underuse", MID, RULES)
        self.assertEqual(lane, "digital")

    def test_escalates_after_unanswered_digital_touches(self):
        self.assertEqual(route(make_account(digital_touches=1), "seat_underuse", NONE, RULES)[0], "digital")
        self.assertEqual(route(make_account(digital_touches=2), "seat_underuse", NONE, RULES)[0], "pooled")
