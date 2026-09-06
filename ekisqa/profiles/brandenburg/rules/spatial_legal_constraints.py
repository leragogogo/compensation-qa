from __future__ import annotations

from ekisqa.model import CompensationFeature, Finding, Severity
from ekisqa.rules.base import DatasetRef, Rule, RuleContext

_FLAECHENPOOL_TYPE = "Flächenpoolkompensation"

_OVERLAP_MIN_AREA_M2 = 100.0
_OVERLAP_MIN_AREA_FRACTION = 0.05

_NEAR_DUPLICATE_MAX_HAUSDORFF_M = 5.0
_NEAR_DUPLICATE_MIN_AREA_RATIO = 0.95
_NEAR_DUPLICATE_MAX_AREA_RATIO = 1.05


def _register_candidates(ctx: RuleContext, query_geometry):
    register = ctx.ekis_register
    if register is None or register.index is None:
        return []
    return [register.features[i] for i in register.index.query(query_geometry)]


class NoOverlapWithRegister(Rule):
    id = "SPATIAL-01"
    category = "SpatialLegalConstraints"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 9
    required_datasets = (DatasetRef("ekis_register"),)

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        threshold = max(
            _OVERLAP_MIN_AREA_FRACTION * feature.geometry.area, _OVERLAP_MIN_AREA_M2
        )
        for candidate in _register_candidates(ctx, feature.geometry):
            if candidate.compensation_id == feature.compensation_id:
                continue
            if candidate.intervention_id == feature.intervention_id:
                continue
            if candidate.geometry is None:
                continue
            intersection_area = feature.geometry.intersection(candidate.geometry).area
            if intersection_area > threshold:
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation=(
                            f"Overlaps existing register compensation "
                            f"{candidate.compensation_id} by {intersection_area:.1f} m^2,"
                            f"exceeding the max Doppelbelegung threshold"
                        ),
                        triggered_field="geometry",
                        observed_value=candidate.compensation_id,
                    )
                ]
        return []


class NearDuplicateDetection(Rule):
    id = "SPATIAL-03"
    category = "SpatialLegalConstraints"
    scope = "state"
    entity = "compensation"
    severity = Severity.WARNING
    stage = 9
    required_datasets = (DatasetRef("ekis_register"),)

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        submitted_area = feature.geometry.area
        query_geometry = feature.geometry.buffer(_NEAR_DUPLICATE_MAX_HAUSDORFF_M)
        for candidate in _register_candidates(ctx, query_geometry):
            if candidate.compensation_id == feature.compensation_id:
                continue
            if candidate.intervention_id == feature.intervention_id:
                continue
            if candidate.geometry is None or candidate.geometry.area <= 0:
                continue
            hausdorff = feature.geometry.hausdorff_distance(candidate.geometry)
            if hausdorff >= _NEAR_DUPLICATE_MAX_HAUSDORFF_M:
                continue
            ratio = submitted_area / candidate.geometry.area
            if not (
                _NEAR_DUPLICATE_MIN_AREA_RATIO
                <= ratio
                <= _NEAR_DUPLICATE_MAX_AREA_RATIO
            ):
                continue
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=(
                        f"Geometry is near-identical to existing register compensation "
                        f"{candidate.compensation_id}. Suspected double-submission"
                    ),
                    triggered_field="geometry",
                    observed_value=candidate.compensation_id,
                )
            ]
        return []


class FlaechenpoolConsistency(Rule):
    id = "SPATIAL-02"
    category = "SpatialLegalConstraints"
    scope = "state"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 9

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        is_pool_type = feature.compensation_type == _FLAECHENPOOL_TYPE
        has_pool_name = bool(feature.area_pool_name and feature.area_pool_name.strip())

        if is_pool_type and not has_pool_name:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=(
                        "Art_der_Kompensation is Flächenpoolkompensation but "
                        "Bezeichnung_des_Flaechenpools is missing"
                    ),
                    triggered_field="area_pool_name",
                )
            ]
        if has_pool_name and not is_pool_type:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=(
                        "Bezeichnung_des_Flaechenpools is populated but Art_der_Kompensation "
                        f"is {feature.compensation_type} and not Flächenpoolkompensation"
                    ),
                    triggered_field="compensation_type",
                    observed_value=feature.compensation_type,
                )
            ]
        return []


class ProtectedAreaIntersection(Rule):
    id = "SPATIAL-04"
    category = "SpatialLegalConstraints"
    scope = "state"
    entity = "compensation"
    severity = Severity.WARNING
    stage = 9
    required_datasets = (DatasetRef("protected_areas"),)

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        for area in ctx.reference.loaded["protected_areas"]:
            if feature.geometry.intersects(area):
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation=(
                            "Compensation polygon intersects a Naturschutzgebiet or Nationalpark."
                            "Verify the parcel"
                        ),
                        triggered_field="geometry",
                    )
                ]
        return []


SPATIAL_LEGAL_CONSTRAINTS_RULES: tuple[type[Rule], ...] = (
    NoOverlapWithRegister,
    FlaechenpoolConsistency,
    NearDuplicateDetection,
    ProtectedAreaIntersection,
)
