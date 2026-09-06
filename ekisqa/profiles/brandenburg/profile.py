from __future__ import annotations

from ekisqa.profiles.base import ProfileReferenceConfig, StateProfile
from ekisqa.profiles.brandenburg.register_client import BrandenburgRegisterClient
from ekisqa.profiles.brandenburg.rules.completeness import COMPLETENESS_RULES
from ekisqa.profiles.brandenburg.rules.domain_validity import DOMAIN_VALIDITY_RULES
from ekisqa.profiles.brandenburg.rules.geometric_semantic import (
    GEOMETRIC_SEMANTIC_RULES,
)
from ekisqa.profiles.brandenburg.rules.referential_integrity import (
    REFERENTIAL_INTEGRITY_RULES,
)
from ekisqa.profiles.brandenburg.rules.spatial_legal_constraints import (
    SPATIAL_LEGAL_CONSTRAINTS_RULES,
)
from ekisqa.profiles.brandenburg.rules.technical_delivery import (
    TECHNICAL_DELIVERY_RULES,
)
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

BRANDENBURG_DISTRICT_CROSSWALK: dict[str, str] = {
    "BAR": "Barnim",
    "BRB": "Brandenburg an der Havel",
    "CB": "Cottbus",
    "LDS": "Dahme-Spreewald",
    "EE": "Elbe-Elster",
    "FF": "Frankfurt (Oder)",
    "HVL": "Havelland",
    "MOL": "Märkisch-Oderland",
    "OHV": "Oberhavel",
    "OSL": "Oberspreewald-Lausitz",
    "LOS": "Oder-Spree",
    "OPR": "Ostprignitz-Ruppin",
    "P": "Potsdam",
    "PM": "Potsdam-Mittelmark",
    "PR": "Prignitz",
    "SPN": "Spree-Neiße",
    "TF": "Teltow-Fläming",
    "UM": "Uckermark",
}


def build_brandenburg_profile() -> StateProfile:
    return StateProfile(
        land_code="BB",
        land_name="Brandenburg",
        crs=BRANDENBURG_CRS,
        schema_adapter=BrandenburgSchemaAdapter(),
        rule_pack=[rule_cls() for rule_cls in BRANDENBURG_RULE_PACK],
        register_client=BrandenburgRegisterClient(),
        reference=ProfileReferenceConfig(
            state_boundary_source="https://isk.geobasis-bb.de/ows/vg_wfs",
            district_boundary_source="https://sgx.geodatenzentrum.de/wfs_vg250",
            protected_areas_source="https://inspire.brandenburg.de/services/schutzg_wfs",
            district_crosswalk=BRANDENBURG_DISTRICT_CROSSWALK,
        ),
    )
