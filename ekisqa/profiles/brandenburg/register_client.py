from __future__ import annotations

from datetime import UTC, datetime

import geopandas as gpd
from shapely.strtree import STRtree

from ekisqa.profiles.brandenburg.schema_adapter import row_to_compensation
from ekisqa.register_data import RegisterSnapshot

_EKIS_WFS_URL = "https://maps.brandenburg.de/services/wfs/ekis"
_KOMPENSATION_TYPENAME = "EKIS:Kompensation"
_TARGET_CRS = "EPSG:25833"


class BrandenburgRegisterClient:
    def __init__(self, base_url: str = _EKIS_WFS_URL) -> None:
        self._base_url = base_url

    def fetch(self) -> RegisterSnapshot:
        url = (
            f"{self._base_url}?service=WFS&version=2.0.0&request=GetFeature"
            f"&typenames={_KOMPENSATION_TYPENAME}&outputFormat=GEOJSON"
            f"&srsName={_TARGET_CRS}"
        )
        gdf = gpd.read_file(url, engine="pyogrio")
        all_features = [
            row_to_compensation(row) for row in gdf.to_dict(orient="records")
        ]
        features = [f for f in all_features if f.geometry is not None]
        index = STRtree([f.geometry for f in features])
        return RegisterSnapshot(
            land_code="BB",
            features=features,
            fetch_timestamp=datetime.now(UTC),
            index=index,
        )
