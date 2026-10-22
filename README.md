# Pooled CS Queue

A small, signal-driven queue for a pooled customer success team. Account signals
fire triggers, each case is scored and routed to the **digital**, **pooled**, or
**named** lane, and a SQL readout reports how the queue is performing.
Every rule lives in [`config/routing_rules.yaml`](config/routing_rules.yaml), so any
number can be audited or changed without touching code.

## Quick start

```bash
pip install -r requirements.txt
python -m pooled_queue queue --explain     # prioritized queue + score math
python -m pooled_queue queue --lane pooled # filter to one lane
python -m pooled_queue readout             # monthly readout (SQLite)
python -m unittest discover -s tests -t .  # run tests
```

## How it works

| Step | Module | What it does |
|------|--------|--------------|
| Triggers | `triggers.py` | stalled onboarding, nothing configured, solo user gone quiet, approaching renewal, cancellation started, seat underuse |
| Enrichment | `enrichment.py` | matches each account to a public company list (Fortune 500 rank) and to internal priority flags |
| Scoring | `scoring.py` | trigger weight x firmographic multiplier + capped ARR bonus + renewal urgency |
| Routing | `routing.py` | first matching rule wins: named (ARR) > save lane > skip-digital tiers > digital > escalate |
| Readout | `readout.py` | volume, time to first response, SLA breach rate, and retention by trigger and tier |

One case is created per account, using its highest-weight trigger. Other triggers that
fired are listed on the case.

### Firmographic scoring

- Fortune 500 top 100: x1.5. Rank 101-500: x1.25.
- Priority tiers (`strategic` x1.6, `design_partner` x1.4, `exec_sponsor` x1.3) come from
  `data/priority_accounts.csv`.
- Only the largest multiplier applies (no stacking), capped at x1.75.
- Top-100 and strategic accounts skip the digital lane.
- Match order: domain first, then normalized company name (suffixes like Inc/Corp/Co ignored).

## Using real company data

`data/fortune500_sample.csv` is **synthetic**: fictional companies so no real firm is
misrepresented. To use real data, replace it with a CSV that has these columns
(headers are case-insensitive; `domain` may also be named `website` or `url`):

```
rank,company,domain,source,as_of
```

Fortune publishes the annual list; public mirrors exist too. Check the terms of
whichever source you use, and fill in `source` and `as_of` so every number is labeled.
Rows with a non-numeric rank are skipped.

## Known limits

- The readout has **no control group**: it shows what happened, not what the queue caused.
  Holding out a random slice of triggered accounts would be the next step.
- Sample data is synthetic, so the readout numbers are illustrative only.
- Rank and priority are static inputs. A real version would refresh them on a schedule.
