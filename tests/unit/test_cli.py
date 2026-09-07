from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Polygon
from typer.testing import CliRunner

from cli.main import app
from tests.fixtures import builders

runner = CliRunner()

_BOWTIE = Polygon(
    [
        (400100, 5800100),
        (400200, 5800200),
        (400200, 5800100),
        (400100, 5800200),
        (400100, 5800100),
    ]
)


def _write_clean_fixture(tmp_path: Path) -> Path:
    intervention, compensation = builders.make_valid_pair()
    return builders.write_gpkg(tmp_path / "clean.gpkg", intervention, compensation)


def _write_invalid_fixture(tmp_path: Path) -> Path:
    intervention, compensation = builders.make_valid_pair()
    compensation = compensation.copy()
    compensation["geometry"] = [_BOWTIE]
    return builders.write_gpkg(tmp_path / "invalid.gpkg", intervention, compensation)


def test_validate_unknown_state_exits_2(tmp_path: Path) -> None:
    fixture = _write_clean_fixture(tmp_path)

    result = runner.invoke(app, ["validate", "--file", str(fixture), "--state", "XX"])

    assert result.exit_code == 2
    assert "XX" in result.output


def test_validate_missing_file_exits_2(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["validate", "--file", str(tmp_path / "does-not-exist.gpkg"), "--state", "BB"]
    )

    assert result.exit_code == 2


def test_validate_clean_dataset_exits_0(tmp_path: Path) -> None:
    fixture = _write_clean_fixture(tmp_path)

    result = runner.invoke(
        app, ["validate", "--file", str(fixture), "--state", "BB", "--format", "json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert all(f["severity"] != "Error" for f in payload["findings"])


def test_validate_dataset_with_error_exits_1(tmp_path: Path) -> None:
    fixture = _write_invalid_fixture(tmp_path)

    result = runner.invoke(
        app, ["validate", "--file", str(fixture), "--state", "BB", "--format", "json"]
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert any(f["rule_id"] == "GEOM-02" and f["severity"] == "Error" for f in payload["findings"])


def test_validate_html_roadmap_smoke_command(tmp_path: Path) -> None:
    fixture = _write_clean_fixture(tmp_path)

    result = runner.invoke(
        app, ["validate", "--file", str(fixture), "--state", "BB", "--format", "html"]
    )

    assert result.exit_code == 0
    assert "<!doctype html>" in result.stdout
    assert "<script" not in result.stdout


def test_validate_rules_filter_restricts_categories(tmp_path: Path) -> None:
    fixture = _write_invalid_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "validate",
            "--file",
            str(fixture),
            "--state",
            "BB",
            "--format",
            "json",
            "--rules",
            "Geometry",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["findings"]
    assert all(f["rule_id"].startswith("GEOM-") for f in payload["findings"])


def test_validate_rules_filter_unknown_category_exits_2(tmp_path: Path) -> None:
    fixture = _write_clean_fixture(tmp_path)

    result = runner.invoke(
        app,
        [
            "validate",
            "--file",
            str(fixture),
            "--state",
            "BB",
            "--rules",
            "NotACategory",
        ],
    )

    assert result.exit_code == 2
    assert "NotACategory" in result.output


def test_validate_gpkg_format_requires_output(tmp_path: Path) -> None:
    fixture = _write_clean_fixture(tmp_path)

    result = runner.invoke(
        app, ["validate", "--file", str(fixture), "--state", "BB", "--format", "gpkg"]
    )

    assert result.exit_code == 2


def test_validate_writes_geojson_pair_to_output_stem(tmp_path: Path) -> None:
    fixture = _write_clean_fixture(tmp_path)
    output = tmp_path / "report"

    result = runner.invoke(
        app,
        [
            "validate",
            "--file",
            str(fixture),
            "--state",
            "BB",
            "--format",
            "geojson",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    kompensation_path = tmp_path / "report.kompensation.geojson"
    eingriff_path = tmp_path / "report.eingriff.geojson"
    assert kompensation_path.exists()
    assert eingriff_path.exists()
    assert json.loads(kompensation_path.read_text())["type"] == "FeatureCollection"
