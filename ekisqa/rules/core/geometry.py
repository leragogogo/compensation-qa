from __future__ import annotations

from itertools import pairwise

from shapely.validation import explain_validity

from ekisqa.model import CompensationFeature, Finding, Severity
from ekisqa.rules.base import Rule, RuleContext


def _polygon_parts(geometry):
    if geometry is None:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return []


class RingClosure(Rule):
    id = "GEOM-01"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        reason = explain_validity(feature.geometry)
        if "closed" in reason.lower():
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=f"Ring is not closed: {reason}",
                    triggered_field="geometry",
                    observed_value=reason,
                )
            ]
        return []


class NoSelfIntersection(Rule):
    id = "GEOM-02"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        reason = explain_validity(feature.geometry)
        if "self-intersection" in reason.lower():
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=f"Ring self-intersects: {reason}",
                    triggered_field="geometry",
                    observed_value=reason,
                )
            ]
        return []


class InteriorRingsWithinExterior(Rule):
    id = "GEOM-03"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        reason = explain_validity(feature.geometry)
        if "hole" in reason.lower() and "outside" in reason.lower():
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=f"Interior ring lies outside exterior ring: {reason}",
                    triggered_field="geometry",
                    observed_value=reason,
                )
            ]
        return []


class NonZeroArea(Rule):
    id = "GEOM-04"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        area = feature.geometry.area
        if area <= 0:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=f"Polygon area is {area} m^2, expected > 0",
                    triggered_field="geometry",
                    observed_value=str(area),
                )
            ]
        return []


class NoDuplicateConsecutiveVertices(Rule):
    id = "GEOM-05"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        for polygon in _polygon_parts(feature.geometry):
            for ring in (polygon.exterior, *polygon.interiors):
                coords = list(ring.coords)
                for a, b in pairwise(coords):
                    if a == b:
                        return [
                            Finding(
                                rule_id=self.id,
                                severity=self.severity,
                                feature_id=feature.compensation_id,
                                land_code=ctx.land_code,
                                explanation=f"Ring contains a duplicate consecutive vertex at {a}",
                                triggered_field="geometry",
                                observed_value=str(a),
                            )
                        ]
        return []


class ExteriorRingOrientation(Rule):
    id = "GEOM-06"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.WARNING
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        for polygon in _polygon_parts(feature.geometry):
            if not polygon.exterior.is_ccw:
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation="Exterior ring is not oriented counter-clockwise",
                        triggered_field="geometry",
                        observed_value="CW",
                    )
                ]
            for interior in polygon.interiors:
                if interior.is_ccw:
                    return [
                        Finding(
                            rule_id=self.id,
                            severity=self.severity,
                            feature_id=feature.compensation_id,
                            land_code=ctx.land_code,
                            explanation="Interior ring is not oriented clockwise",
                            triggered_field="geometry",
                            observed_value="CCW",
                        )
                    ]
        return []


class MinimumAreaThreshold(Rule):
    id = "GEOM-07"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.WARNING
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        area = feature.geometry.area
        if 0 < area < 1:
            return [
                Finding(
                    rule_id=self.id,
                    severity=self.severity,
                    feature_id=feature.compensation_id,
                    land_code=ctx.land_code,
                    explanation=f"Polygon area is {area} m^2, below the 1 m^2 threshold",
                    triggered_field="geometry",
                    observed_value=str(area),
                )
            ]
        return []


class NoDuplicatePolygons(Rule):
    id = "GEOM-08"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.ERROR
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        for other in ctx.compensations:
            if (
                other.compensation_id == feature.compensation_id
                or other.geometry is None
            ):
                continue
            if feature.geometry.equals(other.geometry):
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation=f"Geometry is identical to compensation {other.compensation_id}",
                        triggered_field="geometry",
                        observed_value=other.compensation_id,
                    )
                ]
        return []


class NoOverlapWithinDataset(Rule):
    id = "GEOM-09"
    category = "Geometry"
    scope = "core"
    entity = "compensation"
    severity = Severity.WARNING
    stage = 1

    def check(self, feature: CompensationFeature, ctx: RuleContext) -> list[Finding]:
        if feature.geometry is None:
            return []
        for other in ctx.compensations:
            if (
                other.compensation_id == feature.compensation_id
                or other.geometry is None
            ):
                continue
            if feature.geometry.overlaps(other.geometry):
                return [
                    Finding(
                        rule_id=self.id,
                        severity=self.severity,
                        feature_id=feature.compensation_id,
                        land_code=ctx.land_code,
                        explanation=f"Overlaps compensation {other.compensation_id} within the same dataset",
                        triggered_field="geometry",
                        observed_value=other.compensation_id,
                    )
                ]
        return []


GEOMETRY_RULES: tuple[type[Rule], ...] = (
    RingClosure,
    NoSelfIntersection,
    InteriorRingsWithinExterior,
    NonZeroArea,
    NoDuplicateConsecutiveVertices,
    ExteriorRingOrientation,
    MinimumAreaThreshold,
    NoDuplicatePolygons,
    NoOverlapWithinDataset,
)
