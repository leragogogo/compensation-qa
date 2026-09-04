from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from shapely.geometry import MultiPolygon

from ekisqa.profiles.brandenburg.schema_adapter import BrandenburgSchemaAdapter
from tests.fixtures import builders


def _write_gpkg(tmp_path: Path, intervention, compensation) -> Path:
    return builders.write_gpkg(tmp_path / "data.gpkg", intervention, compensation)


def _write_shp(tmp_path: Path, intervention, compensation) -> Path:
    return builders.write_shapefile_pair(tmp_path / "shp", intervention, compensation)


def _write_gml(tmp_path: Path, intervention, compensation) -> Path:
    return builders.write_gml_pair(tmp_path / "gml", intervention, compensation)


FORMAT_WRITERS = pytest.mark.parametrize(
    "writer", [_write_gpkg, _write_shp, _write_gml], ids=["gpkg", "shapefile", "gml"]
)


@FORMAT_WRITERS
def test_valid_pair_parses_and_joins(tmp_path: Path, writer) -> None:
    intervention, compensation = builders.make_valid_pair()
    path = writer(tmp_path, intervention, compensation)

    compensations, interventions = BrandenburgSchemaAdapter().parse(path)

    assert len(interventions) == 1
    assert len(compensations) == 1

    intervention = interventions[0]
    assert intervention.intervention_id == "E-1"
    assert intervention.project_category == "BImSchG"
    assert intervention.project_type == "Windenergieanlage"
    assert intervention.category_vt == "Neubau"
    assert intervention.category_zb == "Landkreis"
    assert intervention.approval_authority == "Landkreis Potsdam-Mittelmark"
    assert intervention.case_reference == "AZ-2026-001"
    assert intervention.district == "PM"
    assert intervention.legal_basis == "BImSchG"
    assert intervention.approval_date == datetime.date(2026, 3, 1)

    compensation = compensations[0]
    assert compensation.compensation_id == "K-1"
    assert compensation.compensation_type == "Realkompensation"
    assert compensation.case_reference == "AZ-2026-001"
    assert compensation.compensation_name == "Ausgleichsflaeche 1"
    assert compensation.area_pool_name is None
    assert isinstance(compensation.geometry, MultiPolygon)

    assert compensation.linked_intervention is not None
    assert compensation.linked_intervention.intervention_id == "E-1"


def test_orphan_compensation_has_no_linked_intervention(tmp_path: Path) -> None:
    intervention, compensation = builders.make_orphan_compensation()
    path = _write_gpkg(tmp_path, intervention, compensation)

    compensations, interventions = BrandenburgSchemaAdapter().parse(path)

    assert len(interventions) == 1
    assert len(compensations) == 1
    assert compensations[0].linked_intervention is None
