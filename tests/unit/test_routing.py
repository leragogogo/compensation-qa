from __future__ import annotations

from ekisqa.model import CompensationFeature
from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.routing import AxisCondition, AxisFlags, RoutingPreCheck


class _NoOpSchemaAdapter:
    def parse(self, path):
        raise NotImplementedError


class _StubAxisDefinitions:
    def evaluate(self, compensation: CompensationFeature) -> dict:
        return {"axis_c": compensation.compensation_type}


def _profile(axis_definitions=None) -> StateProfile:
    return StateProfile(
        land_code="ZZ",
        land_name="Synthetic",
        crs="EPSG:4326",
        schema_adapter=_NoOpSchemaAdapter(),
        axis_definitions=axis_definitions,
        reference=ProfileReferenceConfig(),
    )


def test_no_condition_always_applies() -> None:
    flags = AxisFlags(flags={})
    assert flags.satisfies(None) is True


def test_condition_matches_resolved_flag() -> None:
    flags = AxisFlags(flags={"axis_c": "Landkreis"})
    condition = AxisCondition(axis="axis_c", values=frozenset({"Landkreis"}))
    assert flags.satisfies(condition) is True


def test_condition_rejects_non_matching_flag() -> None:
    flags = AxisFlags(flags={"axis_c": "Land"})
    condition = AxisCondition(axis="axis_c", values=frozenset({"Landkreis"}))
    assert flags.satisfies(condition) is False


def test_profile_without_axis_definitions_resolves_empty_flags() -> None:
    compensation = CompensationFeature(compensation_id="K-1", geometry=None)
    precheck = RoutingPreCheck(_profile(axis_definitions=None).axis_definitions)

    assert precheck.resolve(compensation) == AxisFlags(flags={})


def test_precheck_resolves_profile_axis_definitions_not_a_hardcoded_condition() -> None:
    compensation = CompensationFeature(
        compensation_id="K-1", geometry=None, compensation_type="Landkreis"
    )
    precheck = RoutingPreCheck(
        _profile(axis_definitions=_StubAxisDefinitions()).axis_definitions
    )
    condition = AxisCondition(axis="axis_c", values=frozenset({"Landkreis"}))

    assert precheck.applies(condition, compensation) is True

    other = CompensationFeature(
        compensation_id="K-2", geometry=None, compensation_type="Land"
    )
    assert precheck.applies(condition, other) is False
