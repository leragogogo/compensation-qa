from __future__ import annotations

from pathlib import Path

from ekisqa.profiles.registry import default_registry
from tests.fixtures import builders


def test_resolve_then_parse_end_to_end(tmp_path: Path) -> None:
    intervention, compensations = builders.make_valid_pair()
    path = builders.write_gpkg(tmp_path / "data.gpkg", intervention, compensations)

    profile = default_registry().resolve("BB")
    compensations, interventions = profile.schema_adapter.parse(path)

    assert len(interventions) == 1
    assert len(compensations) == 1
    assert compensations[0].linked_intervention is interventions[0]
