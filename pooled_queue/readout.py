"""Monthly readout: plain SQL over a case-history CSV, loaded into SQLite."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

HOURS = "(julianday({end}) - julianday(c.created_at)) * 24"

BY_TRIGGER_SQL = f"""
SELECT c.trigger                                              AS trigger,
       COUNT(*)                                               AS cases,
       ROUND(AVG({HOURS.format(end='c.first_response_at')}), 1) AS avg_first_response_hrs,
       ROUND(AVG({HOURS.format(end='c.resolved_at')}), 1)       AS avg_resolution_hrs,
       ROUND(100.0 * SUM(CASE WHEN {HOURS.format(end='c.first_response_at')} > s.first_response_hours
                              THEN 1 ELSE 0 END)
             / COUNT(c.first_response_at), 1)                 AS first_response_breach_pct,
       ROUND(100.0 * SUM(c.account_retained)
             / COUNT(c.account_retained), 1)                  AS retained_pct
FROM cases c
JOIN sla s ON s.trigger = c.trigger
GROUP BY c.trigger
ORDER BY cases DESC, c.trigger;
"""

BY_TIER_SQL = f"""
SELECT c.tier                                                 AS tier,
       COUNT(*)                                               AS cases,
       ROUND(AVG({HOURS.format(end='c.first_response_at')}), 1) AS avg_first_response_hrs,
       ROUND(100.0 * SUM(c.account_retained)
             / COUNT(c.account_retained), 1)                  AS retained_pct
FROM cases c
GROUP BY c.tier
ORDER BY cases DESC, c.tier;
"""


def _blank_to_none(value: str | None):
    value = (value or "").strip()
    return value or None


def run_readout(history_csv: str | Path, rules: dict) -> dict[str, list[dict]]:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    try:
        con.execute(
            """CREATE TABLE cases (
                   case_id TEXT, account_id TEXT, trigger TEXT, lane TEXT, tier TEXT,
                   created_at TEXT, first_response_at TEXT, resolved_at TEXT,
                   account_retained INTEGER)"""
        )
        con.execute("CREATE TABLE sla (trigger TEXT PRIMARY KEY, first_response_hours INTEGER)")
        con.executemany(
            "INSERT INTO sla VALUES (?, ?)",
            [(name, spec["first_response_hours"]) for name, spec in rules["triggers"].items()],
        )
        with open(history_csv, newline="", encoding="utf-8") as fh:
            rows = [
                (
                    r["case_id"], r["account_id"], r["trigger"], r["lane"], r["tier"],
                    r["created_at"],
                    _blank_to_none(r["first_response_at"]),
                    _blank_to_none(r["resolved_at"]),
                    None if _blank_to_none(r["account_retained"]) is None
                    else int(r["account_retained"]),
                )
                for r in csv.DictReader(fh)
            ]
        con.executemany("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?)", rows)
        return {
            "by_trigger": [dict(r) for r in con.execute(BY_TRIGGER_SQL)],
            "by_tier": [dict(r) for r in con.execute(BY_TIER_SQL)],
        }
    finally:
        con.close()
