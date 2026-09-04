from __future__ import annotations

from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.profiles.brandenburg.schema_adapter import (
    BRANDENBURG_CRS,
    BrandenburgSchemaAdapter,
)


def build_brandenburg_profile() -> StateProfile:
    return StateProfile(
        land_code="BB",
        land_name="Brandenburg",
        crs=BRANDENBURG_CRS,
        schema_adapter=BrandenburgSchemaAdapter(),
        rule_pack=[],
        axis_definitions=None,
        register_client=None,
        reference=ProfileReferenceConfig(),
    )
