from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from ekisqa.rules.base import Rule


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    land_code: str
    check_date: date
    register_fetch_timestamp: datetime | None = None


def index_rules(rules: Iterable[Rule]) -> dict[str, Rule]:
    return {rule.id: rule for rule in rules}
