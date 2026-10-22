from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_rules
from .enrichment import Enricher
from .models import load_accounts
from .pipeline import build_queue
from .readout import run_readout

ROOT = Path(__file__).resolve().parent.parent


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("(no rows)")
        return
    headers = list(rows[0])
    widths = {h: max(len(h), *(len(str(r[h])) for r in rows)) for h in headers}
    print("  ".join(h.ljust(widths[h]) for h in headers))
    print("  ".join("-" * widths[h] for h in headers))
    for r in rows:
        print("  ".join(str(r[h]).ljust(widths[h]) for h in headers))


def cmd_queue(args: argparse.Namespace) -> int:
    rules = load_rules(args.rules)
    accounts = load_accounts(args.accounts)
    enricher = Enricher.from_files(args.fortune, args.priority)
    cases = build_queue(accounts, enricher, rules)
    if args.lane:
        cases = [c for c in cases if c.lane == args.lane]
    rows = [
        {
            "#": i,
            "account": c.account_name,
            "trigger": c.primary_trigger,
            "lane": c.lane,
            "score": c.score,
            "1st_resp_hrs": c.first_response_hours,
        }
        for i, c in enumerate(cases, 1)
    ]
    _print_table(rows)
    if args.explain:
        print()
        for c in cases:
            extra = f" (also: {', '.join(c.also_fired)})" if c.also_fired else ""
            print(f"{c.account_name}: {c.explain}{extra}")
            print(f"    lane: {c.lane} - {c.lane_reason}")
    return 0


def cmd_readout(args: argparse.Namespace) -> int:
    rules = load_rules(args.rules)
    result = run_readout(args.history, rules)
    print(f"SOURCE: {args.history} (synthetic sample data, no control group)\n")
    print("By trigger")
    _print_table(result["by_trigger"])
    print("\nBy account tier")
    _print_table(result["by_tier"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pooled_queue", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("queue", help="build and print the prioritized queue")
    q.add_argument("--accounts", default=ROOT / "data/accounts.csv")
    q.add_argument("--fortune", default=ROOT / "data/fortune500_sample.csv")
    q.add_argument("--priority", default=ROOT / "data/priority_accounts.csv")
    q.add_argument("--rules", default=ROOT / "config/routing_rules.yaml")
    q.add_argument("--lane", choices=["digital", "pooled", "named"])
    q.add_argument("--explain", action="store_true", help="show score math and routing reason")
    q.set_defaults(func=cmd_queue)

    r = sub.add_parser("readout", help="print the monthly readout")
    r.add_argument("--history", default=ROOT / "data/case_history.csv")
    r.add_argument("--rules", default=ROOT / "config/routing_rules.yaml")
    r.set_defaults(func=cmd_readout)

    args = parser.parse_args(argv)
    return args.func(args)
