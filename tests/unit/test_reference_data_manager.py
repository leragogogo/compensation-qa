from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.reference.manager import ReferenceDataManager

CRS = "EPSG:25833"


class _NoOpSchemaAdapter:
    def parse(self, path: Path) -> tuple[list, list]:
        raise NotImplementedError("not used by this test")


def _profile(district_crosswalk=None) -> StateProfile:
    return StateProfile(
        land_code="ZZ",
        land_name="Synthetic",
        crs=CRS,
        schema_adapter=_NoOpSchemaAdapter(),
        reference=ProfileReferenceConfig(district_crosswalk=district_crosswalk),
    )


def test_load_returns_empty_reference_data_when_nothing_cached(tmp_path: Path) -> None:
    manager = ReferenceDataManager(_profile(), base_dir=tmp_path)

    data = manager.load()

    assert data.loaded == {}


def test_load_reads_state_boundary(tmp_path: Path) -> None:
    land_dir = tmp_path / "ZZ"
    land_dir.mkdir(parents=True)
    boundary = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
    gpd.GeoDataFrame({"geometry": [boundary]}, crs=CRS).to_file(
        land_dir / "state_boundary.gpkg", driver="GPKG"
    )

    data = ReferenceDataManager(_profile(), base_dir=tmp_path).load()

    assert data.loaded["state_boundary"].equals(boundary)


def test_load_reads_district_boundaries_keyed_by_crosswalk_code(tmp_path: Path) -> None:
    land_dir = tmp_path / "ZZ"
    land_dir.mkdir(parents=True)
    barnim = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    potsdam = Polygon([(20, 0), (30, 0), (30, 10), (20, 10), (20, 0)])
    gpd.GeoDataFrame(
        {"gen": ["Barnim", "Potsdam"], "geometry": [barnim, potsdam]}, crs=CRS
    ).to_file(land_dir / "district_boundaries.gpkg", driver="GPKG")

    profile = _profile(district_crosswalk={"BAR": "Barnim", "P": "Potsdam"})
    data = ReferenceDataManager(profile, base_dir=tmp_path).load()

    districts = data.loaded["district_boundaries"]
    assert set(districts) == {"BAR", "P"}
    assert districts["BAR"].equals(barnim)
    assert districts["P"].equals(potsdam)


def test_load_skips_crosswalk_codes_missing_from_the_cached_layer(
    tmp_path: Path,
) -> None:
    land_dir = tmp_path / "ZZ"
    land_dir.mkdir(parents=True)
    barnim = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    gpd.GeoDataFrame({"gen": ["Barnim"], "geometry": [barnim]}, crs=CRS).to_file(
        land_dir / "district_boundaries.gpkg", driver="GPKG"
    )

    profile = _profile(district_crosswalk={"BAR": "Barnim", "P": "Potsdam"})
    data = ReferenceDataManager(profile, base_dir=tmp_path).load()

    assert set(data.loaded["district_boundaries"]) == {"BAR"}


def test_load_reads_protected_areas_as_a_list(tmp_path: Path) -> None:
    land_dir = tmp_path / "ZZ"
    land_dir.mkdir(parents=True)
    nsg = Polygon([(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)])
    natp = Polygon([(50, 50), (55, 50), (55, 55), (50, 55), (50, 50)])
    gpd.GeoDataFrame({"geometry": [nsg, natp]}, crs=CRS).to_file(
        land_dir / "protected_areas.gpkg", driver="GPKG"
    )

    data = ReferenceDataManager(_profile(), base_dir=tmp_path).load()

    assert len(data.loaded["protected_areas"]) == 2


def test_load_reads_all_three_datasets_together(tmp_path: Path) -> None:
    land_dir = tmp_path / "ZZ"
    land_dir.mkdir(parents=True)
    gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])]},
        crs=CRS,
    ).to_file(land_dir / "state_boundary.gpkg", driver="GPKG")
    gpd.GeoDataFrame(
        {
            "gen": ["Barnim"],
            "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])],
        },
        crs=CRS,
    ).to_file(land_dir / "district_boundaries.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"geometry": [Point(1, 1).buffer(1)]}, crs=CRS).to_file(
        land_dir / "protected_areas.gpkg", driver="GPKG"
    )

    profile = _profile(district_crosswalk={"BAR": "Barnim"})
    data = ReferenceDataManager(profile, base_dir=tmp_path).load()

    assert set(data.loaded) == {
        "state_boundary",
        "district_boundaries",
        "protected_areas",
    }
