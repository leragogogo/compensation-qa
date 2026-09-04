from __future__ import annotations

import pytest

from ekisqa.profiles.brandenburg.schema_adapter import (
    BRANDENBURG_CRS,
    BrandenburgSchemaAdapter,
)
from ekisqa.profiles.registry import (
    UnknownProfileError,
    default_registry,
)


def test_default_registry_resolves_brandenburg() -> None:
    profile = default_registry().resolve("BB")
    assert profile.land_code == "BB"
    assert profile.land_name == "Brandenburg"
    assert profile.crs == BRANDENBURG_CRS
    assert isinstance(profile.schema_adapter, BrandenburgSchemaAdapter)


def test_unknown_land_code_fails_fast() -> None:
    with pytest.raises(UnknownProfileError, match="XX"):
        default_registry().resolve("XX")
