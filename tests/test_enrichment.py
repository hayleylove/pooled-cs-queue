import unittest

from pooled_queue.enrichment import Enricher, normalize_domain, normalize_name
from .helpers import make_account

FORTUNE = [
    {"Rank": "42", "Company": "Acme Holdings, Inc.", "Website": "https://www.acme.example/", "source": "test"},
    {"Rank": "300", "Company": "The Globex Corp", "Website": "", "source": "test"},
    {"Rank": "not-a-number", "Company": "Broken Row", "Website": "broken.example"},
]
PRIORITY = [{"domain": "WWW.Priority.example", "tier": "strategic", "reason": "pilot"}]


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.enricher = Enricher(FORTUNE, PRIORITY)

    def test_normalizers(self):
        self.assertEqual(normalize_domain("https://www.Acme.example/path"), "acme.example")
        self.assertEqual(normalize_name("The Globex Corp."), "globex")

    def test_domain_match_wins(self):
        e = self.enricher.lookup(make_account(name="Something Else", domain="acme.example"))
        self.assertEqual((e.fortune_rank, e.matched_by), (42, "domain"))

    def test_name_fallback_ignores_suffixes(self):
        e = self.enricher.lookup(make_account(name="Globex", domain="unknown.example"))
        self.assertEqual((e.fortune_rank, e.matched_by), (300, "name"))

    def test_malformed_rank_rows_are_skipped(self):
        e = self.enricher.lookup(make_account(name="Broken Row", domain="broken.example"))
        self.assertIsNone(e.fortune_rank)

    def test_priority_tier_and_tags(self):
        e = self.enricher.lookup(make_account(domain="priority.example"))
        self.assertEqual(e.priority_tier, "strategic")
        self.assertIn("priority:strategic", e.tags)

    def test_top100_also_carries_fortune500_tag(self):
        e = self.enricher.lookup(make_account(domain="acme.example"))
        self.assertEqual(e.tags, {"fortune500_top100", "fortune500"})
