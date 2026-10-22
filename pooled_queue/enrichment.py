"""Match accounts to public company data (e.g. a Fortune 500 list) and
internal priority flags. Domain match wins; normalized name is the fallback."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .models import Account

_NAME_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "llc", "ltd", "plc"}


def normalize_domain(value: str) -> str:
    host = value.strip().lower()
    host = re.sub(r"^[a-z]+://", "", host)
    host = host.split("/")[0]
    return host[4:] if host.startswith("www.") else host


def normalize_name(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", value.lower().replace("&", " and ")).split()
    if text and text[0] == "the":
        text = text[1:]
    while text and text[-1] in _NAME_SUFFIXES:
        text.pop()
    return " ".join(text)


@dataclass(frozen=True)
class Enrichment:
    fortune_rank: int | None = None
    fortune_source: str = ""
    priority_tier: str | None = None
    priority_reason: str = ""
    matched_by: str = ""

    @property
    def tags(self) -> set[str]:
        tags: set[str] = set()
        if self.fortune_rank is not None:
            if self.fortune_rank <= 100:
                tags.add("fortune500_top100")
            if self.fortune_rank <= 500:
                tags.add("fortune500")
        if self.priority_tier:
            tags.add(f"priority:{self.priority_tier}")
        return tags


def _pick(row: dict, *names: str) -> str:
    lowered = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for name in names:
        if name in lowered:
            return lowered[name]
    return ""


class Enricher:
    def __init__(self, fortune_rows: list[dict], priority_rows: list[dict]):
        self._fortune_by_domain: dict[str, dict] = {}
        self._fortune_by_name: dict[str, dict] = {}
        for row in fortune_rows:
            rank = _pick(row, "rank")
            if not rank.isdigit() or int(rank) < 1:
                continue  # skip malformed rows rather than guessing
            entry = {"rank": int(rank), "source": _pick(row, "source")}
            domain = normalize_domain(_pick(row, "domain", "website", "url"))
            if domain:
                self._fortune_by_domain[domain] = entry
            name = normalize_name(_pick(row, "company", "name"))
            if name:
                self._fortune_by_name[name] = entry
        self._priority_by_domain = {
            normalize_domain(_pick(r, "domain")): {
                "tier": _pick(r, "tier"),
                "reason": _pick(r, "reason"),
            }
            for r in priority_rows
            if _pick(r, "domain")
        }

    @classmethod
    def from_files(cls, fortune_path: str | Path, priority_path: str | Path) -> "Enricher":
        return cls(_read_csv(fortune_path), _read_csv(priority_path))

    def lookup(self, account: Account) -> Enrichment:
        domain = normalize_domain(account.domain)
        fortune, matched_by = self._fortune_by_domain.get(domain), "domain"
        if fortune is None:
            fortune = self._fortune_by_name.get(normalize_name(account.name))
            matched_by = "name"
        priority = self._priority_by_domain.get(domain)
        return Enrichment(
            fortune_rank=fortune["rank"] if fortune else None,
            fortune_source=fortune["source"] if fortune else "",
            priority_tier=priority["tier"] if priority else None,
            priority_reason=priority["reason"] if priority else "",
            matched_by=matched_by if fortune else "",
        )


def _read_csv(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
