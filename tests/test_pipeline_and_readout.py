import csv
import tempfile
import unittest
from pathlib import Path

from pooled_queue.config import load_rules
from pooled_queue.enrichment import Enricher
from pooled_queue.pipeline import build_queue
from pooled_queue.readout import run_readout
from .helpers import RULES, ROOT, make_account


class PipelineTests(unittest.TestCase):
    def test_one_case_per_account_sorted_by_score(self):
        accounts = [
            make_account(account_id="A", cancellation_started=True),
            make_account(account_id="B", seats_active=2),
            make_account(account_id="C"),  # healthy
        ]
        cases = build_queue(accounts, Enricher([], []), RULES)
        self.assertEqual([c.account_id for c in cases], ["A", "B"])
        self.assertEqual(cases[0].primary_trigger, "cancellation_started")

    def test_sample_data_runs_end_to_end(self):
        from pooled_queue.models import load_accounts
        enricher = Enricher.from_files(ROOT / "data/fortune500_sample.csv", ROOT / "data/priority_accounts.csv")
        cases = build_queue(load_accounts(ROOT / "data/accounts.csv"), enricher, RULES)
        self.assertTrue(cases)
        self.assertEqual(cases, sorted(cases, key=lambda c: (-c.score, c.account_id)))


class ConfigTests(unittest.TestCase):
    def test_unknown_trigger_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.yaml"
            text = (ROOT / "config/routing_rules.yaml").read_text()
            path.write_text(text.replace("seat_underuse:", "made_up_trigger:", 1))
            with self.assertRaises(ValueError):
                load_rules(path)


class ReadoutTests(unittest.TestCase):
    def test_counts_breaches_and_retention(self):
        header = ["case_id", "account_id", "trigger", "lane", "tier",
                  "created_at", "first_response_at", "resolved_at", "account_retained"]
        rows = [
            ["1", "A", "renewal_approaching", "pooled", "none", "2026-09-01 09:00", "2026-09-01 19:00", "2026-09-03 09:00", "1"],
            ["2", "B", "renewal_approaching", "pooled", "none", "2026-09-01 09:00", "2026-09-03 09:00", "2026-09-05 09:00", "0"],
            ["3", "C", "renewal_approaching", "pooled", "none", "2026-09-01 09:00", "", "", ""],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.csv"
            with open(path, "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(header)
                writer.writerows(rows)
            result = run_readout(path, RULES)["by_trigger"][0]
        self.assertEqual(result["cases"], 3)
        self.assertEqual(result["avg_first_response_hrs"], 29.0)   # (10h + 48h) / 2
        self.assertEqual(result["first_response_breach_pct"], 50.0)  # 48h > 24h SLA, 1 of 2
        self.assertEqual(result["retained_pct"], 50.0)             # unresolved case excluded


if __name__ == "__main__":
    unittest.main()
