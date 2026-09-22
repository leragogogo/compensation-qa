from __future__ import annotations

import csv
from pathlib import Path

from ekisqa.profiles.registry import default_registry

_FLAECHENPOOL_TYPE = "Flächenpoolkompensation"


def spatial_02_selectivity(state: str = "BB") -> dict[str, int]:
    profile = default_registry().resolve(state)
    snapshot = profile.register_client.fetch()

    buckets = {
        "pool_type_with_name": 0,
        "pool_type_without_name": 0,
        "non_pool_with_name": 0,
        "non_pool_without_name": 0,
    }
    for f in snapshot.features:
        is_pool = f.compensation_type == _FLAECHENPOOL_TYPE
        has_name = bool(f.area_pool_name and f.area_pool_name.strip())
        key = ("pool_type" if is_pool else "non_pool") + (
            "_with_name" if has_name else "_without_name"
        )
        buckets[key] += 1

    buckets["_total"] = len(snapshot.features)
    return buckets


def main() -> None:
    print("SPATIAL-02 (Flaechenpool consistency) selectivity, live BB register:")
    buckets = spatial_02_selectivity()
    total = buckets["_total"]
    axis_condition_count = (
        buckets["pool_type_with_name"] + buckets["pool_type_without_name"]
    )

    rows = [
        {
            "rule_id": "SPATIAL-02",
            "population": "Original Axis B condition (compensation_type = Flaechenpoolkompensation)",
            "count": axis_condition_count,
            "pct_of_register": round(axis_condition_count / total * 100, 2),
        },
        {
            "rule_id": "SPATIAL-02",
            "population": "pool_type_with_name (well-formed, no finding)",
            "count": buckets["pool_type_with_name"],
            "pct_of_register": round(buckets["pool_type_with_name"] / total * 100, 2),
        },
        {
            "rule_id": "SPATIAL-02",
            "population": "pool_type_without_name (finding: direction 1)",
            "count": buckets["pool_type_without_name"],
            "pct_of_register": round(
                buckets["pool_type_without_name"] / total * 100, 2
            ),
        },
        {
            "rule_id": "SPATIAL-02",
            "population": "non_pool_with_name (finding: direction 2 -- outside the original axis condition)",
            "count": buckets["non_pool_with_name"],
            "pct_of_register": round(buckets["non_pool_with_name"] / total * 100, 2),
        },
        {
            "rule_id": "SPATIAL-02",
            "population": "non_pool_without_name (ordinary Realkompensation, untouched)",
            "count": buckets["non_pool_without_name"],
            "pct_of_register": round(buckets["non_pool_without_name"] / total * 100, 2),
        },
        {
            "rule_id": "COMPLETE-07",
            "population": "UNMEASURABLE",
            "count": None,
            "pct_of_register": None,
        },
        {
            "rule_id": "REF-02",
            "population": "UNMEASURABLE",
            "count": None,
            "pct_of_register": None,
        },
    ]

    for row in rows:
        pct = (
            f"{row['pct_of_register']:.2f}%"
            if row["pct_of_register"] is not None
            else "n/a"
        )
        count = row["count"] if row["count"] is not None else "n/a"
        print(f"  [{row['rule_id']:<11}] {count!s:>6}  {pct:>7}  {row['population']}")

    out_path = Path("eval/results/rule_selectivity.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["rule_id", "population", "count", "pct_of_register"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
