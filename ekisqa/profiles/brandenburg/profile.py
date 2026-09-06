from __future__ import annotations

from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.profiles.brandenburg.rules.completeness import COMPLETENESS_RULES
from ekisqa.profiles.brandenburg.rules.domain_validity import DOMAIN_VALIDITY_RULES
from ekisqa.profiles.brandenburg.rules.geometric_semantic import GEOMETRIC_SEMANTIC_RULES
from ekisqa.profiles.brandenburg.rules.referential_integrity import (
    REFERENTIAL_INTEGRITY_RULES,
)
from ekisqa.profiles.brandenburg.rules.spatial_legal_constraints import (
    SPATIAL_LEGAL_CONSTRAINTS_RULES,
)
from ekisqa.profiles.brandenburg.rules.technical_delivery import TECHNICAL_DELIVERY_RULES
from ekisqa.profiles.brandenburg.rules.temporal import TEMPORAL_RULES
from ekisqa.profiles.brandenburg.schema_adapter import (
    BRANDENBURG_CRS,
    BrandenburgSchemaAdapter,
)

BRANDENBURG_RULE_PACK: tuple[type, ...] = (
    *DOMAIN_VALIDITY_RULES,
    *COMPLETENESS_RULES,
    *TECHNICAL_DELIVERY_RULES,
    *TEMPORAL_RULES,
    *REFERENTIAL_INTEGRITY_RULES,
    *GEOMETRIC_SEMANTIC_RULES,
    *SPATIAL_LEGAL_CONSTRAINTS_RULES,
)


def build_brandenburg_profile() -> StateProfile:
    return StateProfile(
        land_code="BB",
        land_name="Brandenburg",
        crs=BRANDENBURG_CRS,
        schema_adapter=BrandenburgSchemaAdapter(),
        rule_pack=[rule_cls() for rule_cls in BRANDENBURG_RULE_PACK],
        axis_definitions=None,
        register_client=None,
        reference=ProfileReferenceConfig(),
    )
