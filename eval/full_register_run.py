from __future__ import annotations

import argparse
import csv
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ekisqa.context import ValidationContext
from ekisqa.profiles.registry import default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.rules.base import DatasetRef, Rule
from ekisqa.rules.core import CORE_RULES

EXCLUDED_RULE_IDS: frozenset[str] = frozenset({"REF-01"})
QUADRATIC_RULE_IDS: frozenset[str] = frozenset({"GEOM-08", "GEOM-09", "REF-03"})


def eligible_rules(all_rules: list[Rule], skip_quadratic: bool) -> list[Rule]:
    excluded = set(EXCLUDED_RULE_IDS)
    if skip_quadratic:
        excluded |= QUADRATIC_RULE_IDS

    eligible = []
    for rule in all_rules:
        if rule.entity != "compensation":
            continue
        if rule.id in excluded:
            continue
        if DatasetRef("ekis_register") in rule.required_datasets:
            continue
        eligible.append(rule)
    return eligible


def run(
    state: str, limit: int | None, skip_quadratic: bool
) -> tuple[list, dict[str, float], list[Rule], int]:
    profile = default_registry().resolve(state)
    if profile.register_client is None:
        raise SystemExit(f"{state} has no register client configured.")

    t0 = time.monotonic()
    snapshot = profile.register_client.fetch()
    fetch_seconds = time.monotonic() - t0

    compensations = snapshot.features[:limit] if limit else snapshot.features

    reference = ReferenceDataManager(profile).load()

    core_rules = [rule_cls() for rule_cls in CORE_RULES]
    all_rules = [*core_rules, *profile.rule_pack]
    rules = eligible_rules(all_rules, skip_quadratic)

    context = ValidationContext(
        profile=profile,
        compensations=compensations,
        interventions=[],
        check_date=datetime.now(UTC).date(),
        reference=reference,
        ekis_register=None,
    )

    findings = []
    timings: dict[str, float] = {"_fetch": fetch_seconds}
    for rule in rules:
        t0 = time.monotonic()
        for record in compensations:
            findings.extend(rule.check(record, context))
        timings[rule.id] = time.monotonic() - t0

    return findings, timings, rules, len(compensations)


def write_results(
    findings: list,
    timings: dict[str, float],
    rules: list[Rule],
    n_records: int,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter((f.rule_id, f.severity) for f in findings)

    rows = [
        {
            "rule_id": "_fetch",
            "category": "",
            "severity": "",
            "count": "",
            "pct_of_register": "",
            "seconds": round(timings["_fetch"], 3),
        }
    ]
    for rule in sorted(rules, key=lambda r: r.id):
        count = sum(n for (rid, _sev), n in counts.items() if rid == rule.id)
        pct = (count / n_records * 100) if n_records else 0.0
        rows.append(
            {
                "rule_id": rule.id,
                "category": rule.category,
                "severity": rule.severity.value,
                "count": count,
                "pct_of_register": round(pct, 3),
                "seconds": round(timings.get(rule.id, 0.0), 3),
            }
        )

    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rule_id",
                "category",
                "severity",
                "count",
                "pct_of_register",
                "seconds",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--state", default="BB")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only validate the first N register records.",
    )
    parser.add_argument(
        "--skip-quadratic",
        action="store_true",
        help="Skip GEOM-08, GEOM-09, REF-03",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("eval/results/full_register_findings.csv"),
    )
    args = parser.parse_args()

    findings, timings, rules, n_records = run(
        args.state, args.limit, args.skip_quadratic
    )
    write_results(findings, timings, rules, n_records, args.out)


if __name__ == "__main__":
    main()
