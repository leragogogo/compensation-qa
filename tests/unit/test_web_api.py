from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from shapely.geometry import Polygon

from tests.fixtures import builders
from web.api.main import app

client = TestClient(app)

_BOWTIE = Polygon(
    [
        (400100, 5800100),
        (400200, 5800200),
        (400200, 5800100),
        (400100, 5800200),
        (400100, 5800100),
    ]
)


def _clean_fixture_bytes(tmp_path: Path) -> bytes:
    intervention, compensation = builders.make_valid_pair()
    path = builders.write_gpkg(tmp_path / "clean.gpkg", intervention, compensation)
    return path.read_bytes()


def _invalid_fixture_bytes(tmp_path: Path) -> bytes:
    intervention, compensation = builders.make_valid_pair()
    compensation = compensation.copy()
    compensation["geometry"] = [_BOWTIE]
    path = builders.write_gpkg(tmp_path / "invalid.gpkg", intervention, compensation)
    return path.read_bytes()


def test_list_lands_includes_bb() -> None:
    response = client.get("/api/lands")

    assert response.status_code == 200
    assert "BB" in response.json()["land_codes"]


def test_validate_unknown_state_returns_404(tmp_path: Path) -> None:
    response = client.post(
        "/api/validate",
        files={
            "file": (
                "clean.gpkg",
                _clean_fixture_bytes(tmp_path),
                "application/geopackage+sqlite3",
            )
        },
        data={"state": "XX"},
    )

    assert response.status_code == 404
    assert "XX" in response.json()["detail"]


def test_validate_rejects_non_gpkg_upload() -> None:
    response = client.post(
        "/api/validate",
        files={
            "file": ("clean.shp", b"not a real shapefile", "application/octet-stream")
        },
        data={"state": "BB"},
    )

    assert response.status_code == 400


def test_validate_clean_dataset_returns_full_payload(tmp_path: Path) -> None:
    response = client.post(
        "/api/validate",
        files={
            "file": (
                "clean.gpkg",
                _clean_fixture_bytes(tmp_path),
                "application/geopackage+sqlite3",
            )
        },
        data={"state": "BB"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["land_code"] == "BB"
    assert body["summary"]["error"] == 0
    assert all(f["severity"] != "Error" for f in body["findings"])
    assert body["map"]["kompensation"]["type"] == "FeatureCollection"
    assert body["map"]["eingriff"]["type"] == "FeatureCollection"
    assert "<!doctype html>" in body["reports"]["html"]
    assert set(body["reports"]["geojson"]) == {"kompensation", "eingriff"}
    assert body["reports"]["gpkg_base64"]


def test_validate_dataset_with_error_surfaces_in_summary_and_map(
    tmp_path: Path,
) -> None:
    response = client.post(
        "/api/validate",
        files={
            "file": (
                "invalid.gpkg",
                _invalid_fixture_bytes(tmp_path),
                "application/geopackage+sqlite3",
            )
        },
        data={"state": "BB"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["error"] >= 1
    assert any(f["rule_id"] == "GEOM-02" for f in body["findings"])

    kompensation_features = body["map"]["kompensation"]["features"]
    k1 = next(
        f for f in kompensation_features if f["properties"]["feature_id"] == "K-1"
    )
    assert k1["properties"]["qa_status"] == "Error"

    lon, lat = k1["geometry"]["coordinates"][0][0][0]
    assert -180 <= lon <= 180
    assert -90 <= lat <= 90


def test_validate_invalid_check_date_returns_400(tmp_path: Path) -> None:
    response = client.post(
        "/api/validate",
        files={
            "file": (
                "clean.gpkg",
                _clean_fixture_bytes(tmp_path),
                "application/geopackage+sqlite3",
            )
        },
        data={"state": "BB", "check_date": "not-a-date"},
    )

    assert response.status_code == 400
