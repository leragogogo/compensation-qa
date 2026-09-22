from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

from ekisqa.context import ValidationContext
from ekisqa.model import CompensationFeature, InterventionFeature
from ekisqa.profiles.registry import default_registry
from ekisqa.reference.manager import ReferenceDataManager
from ekisqa.register_data import RegisterSnapshot
from ekisqa.rules.core import CORE_RULES
from ekisqa.rules.registry import CoreRuleRegistry, StageRunner

CHECK_DATE = date(2026, 6, 1)
BASE_X, BASE_Y = 400100.0, 5800100.0
SIDE = 100.0


def _square(x: float, y: float, side: float = SIDE) -> Polygon:
    return Polygon([(x, y), (x + side, y), (x + side, y + side), (x, y + side), (x, y)])


def clean_pair(
    i: int, x: float | None = None, y: float | None = None
) -> tuple[CompensationFeature, InterventionFeature]:
    x = BASE_X + i * 500 if x is None else x
    y = BASE_Y if y is None else y
    case_ref = f"AZ-CLEAN-{i:03d}"

    intervention = InterventionFeature(
        intervention_id=f"E-{i}",
        geometry=Point(x - 30, y - 30),
        project_category="BImSchG",
        project_type="Windenergieanlage",
        project_name="Injected-defect eval",
        category_vt="Neubau",
        category_zb="Bund",
        approval_authority="Landesamt fuer Umwelt",
        case_reference=case_ref,
        additional_case_reference=None,
        approval_date=date(2026, 1, 1),
        district="PM",
        legal_basis="BImSchG",
        remarks=None,
    )
    compensation = CompensationFeature(
        compensation_id=f"K-{i}",
        geometry=_square(x, y),
        compensation_type="Realkompensation",
        project_name="Injected-defect eval",
        case_reference=case_ref,
        compensation_name=f"Flaeche {i}",
        area_pool_name=None,
        intervention_id=None,
        linked_intervention=intervention,
    )
    return compensation, intervention


@dataclass
class Scenario:
    name: str
    rule_id: str
    mutate: object
    uses_register: bool = False


def _mutate_geom02(comps, ivs, reg):
    comps[-1].geometry = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])


def _mutate_geom03(comps, ivs, reg):
    shell = comps[-1].geometry
    hole = [
        [
            (shell.bounds[2] + 500, shell.bounds[3] + 500),
            (shell.bounds[2] + 510, shell.bounds[3] + 500),
            (shell.bounds[2] + 510, shell.bounds[3] + 510),
            (shell.bounds[2] + 500, shell.bounds[3] + 510),
            (shell.bounds[2] + 500, shell.bounds[3] + 500),
        ]
    ]
    comps[-1].geometry = Polygon(list(shell.exterior.coords), hole)


def _mutate_geom04(comps, ivs, reg):
    x, y = BASE_X + 9000, BASE_Y
    comps[-1].geometry = Polygon([(x, y), (x + 10, y), (x + 20, y), (x, y)])


def _mutate_geom05(comps, ivs, reg):
    coords = list(comps[-1].geometry.exterior.coords)
    coords.insert(1, coords[1])
    comps[-1].geometry = Polygon(coords)


def _mutate_geom06(comps, ivs, reg):
    coords = list(comps[-1].geometry.exterior.coords)[::-1]
    comps[-1].geometry = Polygon(coords)


def _mutate_geom07(comps, ivs, reg):
    x, y = BASE_X + 9500, BASE_Y
    comps[-1].geometry = _square(x, y, side=0.5)


def _mutate_geom08(comps, ivs, reg):
    comps[-1].geometry = comps[0].geometry


def _mutate_geom09(comps, ivs, reg):
    other = comps[0].geometry
    x0, y0 = other.exterior.coords[0]
    comps[-1].geometry = _square(x0 + SIDE / 2, y0)


def _mutate_domain01(comps, ivs, reg):
    comps[-1].compensation_type = "Ausgleichsmassnahme"


def _mutate_domain02_comp(comps, ivs, reg):
    comps[-1].case_reference = "AZ-" + "9" * 60


def _mutate_domain02_int(comps, ivs, reg):
    ivs[-1].case_reference = "AZ-" + "9" * 60


def _mutate_complete01_comp(comps, ivs, reg):
    comps[-1].geometry = None


def _mutate_complete01_int(comps, ivs, reg):
    ivs[-1].geometry = None


def _mutate_complete02(comps, ivs, reg):
    ivs[-1].approval_authority = None


def _mutate_complete03_comp(comps, ivs, reg):
    comps[-1].case_reference = None


def _mutate_complete03_int(comps, ivs, reg):
    ivs[-1].case_reference = None


def _mutate_complete04(comps, ivs, reg):
    ivs[-1].approval_date = None


def _mutate_complete05(comps, ivs, reg):
    comps[-1].compensation_type = None


def _mutate_complete06(comps, ivs, reg):
    ivs[-1].legal_basis = None


def _mutate_complete07(comps, ivs, reg):
    ivs[-1].legal_basis = "BauGB"


def _mutate_ref01(comps, ivs, reg):
    comps[-1].linked_intervention = None
    comps[-1].case_reference = "AZ-DOES-NOT-EXIST"


def _mutate_ref02(comps, ivs, reg):
    ivs[-1].category_zb = "Landkreis"
    ivs[-1].district = "P"
    ivs[-1].geometry = Point(BASE_X - 30, BASE_Y - 30)


def _mutate_ref03(comps, ivs, reg):
    comps[-1].compensation_id = None


def _mutate_tech02(comps, ivs, reg):
    comps[-1].geometry = Point(BASE_X, BASE_Y)


def _mutate_tech03(comps, ivs, reg):
    ivs[-1].geometry = comps[-1].geometry


def _mutate_temporal01(comps, ivs, reg):
    ivs[-1].approval_date = date(2099, 1, 1)


def _mutate_geosem01(comps, ivs, reg):
    comps[-1].geometry = _square(700000.0, 5300000.0)


def _mutate_spatial02(comps, ivs, reg):
    comps[-1].compensation_type = "Flächenpoolkompensation"
    comps[-1].area_pool_name = None


def _mutate_spatial04(comps, ivs, reg, protected_polygon):
    c = protected_polygon.centroid
    comps[-1].geometry = _square(c.x - 5, c.y - 5, side=10)


def _mutate_spatial01(comps, ivs, reg):
    comps[-1].geometry = reg.features[0].geometry
    comps[-1].intervention_id = "DIFFERENT"


def _mutate_spatial03(comps, ivs, reg):
    shifted = [(x + 2.0, y) for x, y in reg.features[0].geometry.exterior.coords]
    comps[-1].geometry = Polygon(shifted)
    comps[-1].intervention_id = "DIFFERENT"


def build_register_snapshot() -> RegisterSnapshot:
    existing = CompensationFeature(
        compensation_id="EXISTING-1",
        geometry=_square(BASE_X + 20000, BASE_Y, side=200),
        compensation_type="Realkompensation",
        case_reference="AZ-EXISTING-1",
        intervention_id="EXISTING-INT-1",
    )
    return RegisterSnapshot(
        land_code="BB",
        features=[existing],
        fetch_timestamp=None,
        index=STRtree([existing.geometry]),
    )


def run_scenario(
    rule_id: str,
    mutate,
    profile,
    reference,
    register: RegisterSnapshot | None,
    core_rules,
    n_siblings: int = 4,
) -> dict:
    comps = []
    ivs = []
    for i in range(n_siblings):
        c, iv = clean_pair(i)
        comps.append(c)
        ivs.append(iv)
    sibling_ids = {c.compensation_id for c in comps} | {
        iv.intervention_id for iv in ivs
    }
    if rule_id in ("GEOM-08", "GEOM-09"):
        sibling_ids.discard(comps[0].compensation_id)

    target_c, target_iv = clean_pair(n_siblings)
    comps.append(target_c)
    ivs.append(target_iv)

    mutate(comps, ivs, register)

    context = ValidationContext(
        profile=profile,
        compensations=comps,
        interventions=ivs,
        check_date=CHECK_DATE,
        reference=reference,
        ekis_register=register,
    )
    findings = StageRunner(CoreRuleRegistry(rules=core_rules)).run(context)

    is_skip_marker = lambda f: f.explanation is not None and f.explanation.startswith(
        "Skipped "
    )
    real_findings = [f for f in findings if not is_skip_marker(f)]
    target_findings = [f for f in real_findings if f.feature_id not in sibling_ids]
    sibling_findings = [f for f in real_findings if f.feature_id in sibling_ids]

    recall = any(f.rule_id == rule_id for f in target_findings)
    collateral = sorted({f.rule_id for f in target_findings if f.rule_id != rule_id})
    siblings_clean = len(sibling_findings) == 0

    return {
        "rule_id": rule_id,
        "recall": recall,
        "siblings_clean": siblings_clean,
        "collateral_rules": ",".join(collateral),
        "sibling_finding_count": len(sibling_findings),
    }


def main() -> None:
    profile = default_registry().resolve("BB")
    reference = ReferenceDataManager(profile).load()
    core_rules = [rule_cls() for rule_cls in CORE_RULES]
    register = build_register_snapshot()

    protected = reference.loaded.get("protected_areas")
    protected_polygon = protected[0] if protected else None

    scenarios: list[tuple[str, str, object]] = [
        ("GEOM-02", "GEOM-02", _mutate_geom02),
        ("GEOM-03", "GEOM-03", _mutate_geom03),
        ("GEOM-04", "GEOM-04", _mutate_geom04),
        ("GEOM-05", "GEOM-05", _mutate_geom05),
        ("GEOM-06", "GEOM-06", _mutate_geom06),
        ("GEOM-07", "GEOM-07", _mutate_geom07),
        ("GEOM-08", "GEOM-08", _mutate_geom08),
        ("GEOM-09", "GEOM-09", _mutate_geom09),
        ("DOMAIN-01", "DOMAIN-01", _mutate_domain01),
        ("DOMAIN-02-compensation", "DOMAIN-02", _mutate_domain02_comp),
        ("DOMAIN-02-intervention", "DOMAIN-02", _mutate_domain02_int),
        ("COMPLETE-01-compensation", "COMPLETE-01", _mutate_complete01_comp),
        ("COMPLETE-01-intervention", "COMPLETE-01", _mutate_complete01_int),
        ("COMPLETE-02", "COMPLETE-02", _mutate_complete02),
        ("COMPLETE-03-compensation", "COMPLETE-03", _mutate_complete03_comp),
        ("COMPLETE-03-intervention", "COMPLETE-03", _mutate_complete03_int),
        ("COMPLETE-04", "COMPLETE-04", _mutate_complete04),
        ("COMPLETE-05", "COMPLETE-05", _mutate_complete05),
        ("COMPLETE-06", "COMPLETE-06", _mutate_complete06),
        ("COMPLETE-07", "COMPLETE-07", _mutate_complete07),
        ("REF-01", "REF-01", _mutate_ref01),
        ("REF-02", "REF-02", _mutate_ref02),
        ("REF-03", "REF-03", _mutate_ref03),
        ("TECH-02", "TECH-02", _mutate_tech02),
        ("TECH-03", "TECH-03", _mutate_tech03),
        ("TEMPORAL-01", "TEMPORAL-01", _mutate_temporal01),
        ("GEOSEM-01", "GEOSEM-01", _mutate_geosem01),
        ("SPATIAL-02", "SPATIAL-02", _mutate_spatial02),
        ("SPATIAL-01", "SPATIAL-01", _mutate_spatial01),
        ("SPATIAL-03", "SPATIAL-03", _mutate_spatial03),
    ]
    if protected_polygon is not None:
        scenarios.append(
            (
                "SPATIAL-04",
                "SPATIAL-04",
                lambda comps, ivs, reg, p=protected_polygon: _mutate_spatial04(
                    comps, ivs, reg, p
                ),
            )
        )

    rows = []
    for name, rule_id, mutate in scenarios:
        needs_register = rule_id in ("SPATIAL-01", "SPATIAL-03")
        result = run_scenario(
            rule_id,
            mutate,
            profile,
            reference,
            register if needs_register else None,
            core_rules,
        )
        result["scenario"] = name
        rows.append(result)
        status = "PASS" if result["recall"] and result["siblings_clean"] else "FAIL"
        print(
            f"[{status}] {name:<28} recall={result['recall']!s:<6} "
            f"siblings_clean={result['siblings_clean']!s:<6} "
            f"collateral={result['collateral_rules'] or '-'}"
        )

    print("\nUntested (excluded, not silently skipped):")
    print(
        "  GEOM-01 -- unreachable: Shapely refuses to construct, or auto-closes, an open ring"
    )
    print(
        "  TECH-01 -- CRS mismatch check, operates on file I/O layer, not a feature-level defect"
    )

    out_path = Path("eval/results/injected_defects.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scenario",
                "rule_id",
                "recall",
                "siblings_clean",
                "collateral_rules",
                "sibling_finding_count",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {out_path}")

    n = len(rows)
    recall_n = sum(1 for r in rows if r["recall"])
    clean_n = sum(1 for r in rows if r["siblings_clean"])
    print(f"\nRecall: {recall_n}/{n} scenarios ({recall_n / n * 100:.1f}%)")
    print(f"Siblings stayed clean: {clean_n}/{n} scenarios ({clean_n / n * 100:.1f}%)")


if __name__ == "__main__":
    main()
