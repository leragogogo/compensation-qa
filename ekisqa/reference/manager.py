from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from ekisqa.profiles.base import StateProfile
from ekisqa.register_data import ReferenceData

_TARGET_CRS = "EPSG:25833"

_STATE_BOUNDARY_TYPENAME = "app:bb_flaeche"
_DISTRICT_TYPENAME = "vg250:vg250_krs"
_PROTECTED_AREA_TYPENAMES = ("app:nsg", "app:natp")


def _fetch_layer(base_url: str, typename: str) -> gpd.GeoDataFrame:
    url = (
        f"{base_url}?service=WFS&version=2.0.0&request=GetFeature"
        f"&typenames={typename}&srsName={_TARGET_CRS}"
    )
    gdf = gpd.read_file(url, engine="pyogrio")
    if gdf.crs is None:
        gdf = gdf.set_crs(_TARGET_CRS)
    elif gdf.crs.to_string() != _TARGET_CRS:
        gdf = gdf.to_crs(_TARGET_CRS)
    return gdf


class ReferenceDataManager:
    def __init__(
        self, profile: StateProfile, base_dir: Path | str = "reference"
    ) -> None:
        self._profile = profile
        self._dir = Path(base_dir) / profile.land_code

    def update(self) -> list[str]:
        config = self._profile.reference
        self._dir.mkdir(parents=True, exist_ok=True)
        written: list[str] = []

        if config.state_boundary_source:
            gdf = _fetch_layer(config.state_boundary_source, _STATE_BOUNDARY_TYPENAME)
            gdf.to_file(self._dir / "state_boundary.gpkg", driver="GPKG")
            written.append("state_boundary")

        if config.district_boundary_source:
            gdf = _fetch_layer(config.district_boundary_source, _DISTRICT_TYPENAME)
            if config.district_crosswalk:
                gdf = gdf[gdf["gen"].isin(config.district_crosswalk.values())]
            gdf.to_file(self._dir / "district_boundaries.gpkg", driver="GPKG")
            written.append("district_boundaries")

        if config.protected_areas_source:
            frames = [
                _fetch_layer(config.protected_areas_source, typename)
                for typename in _PROTECTED_AREA_TYPENAMES
            ]
            combined = gpd.GeoDataFrame(
                pd.concat(frames, ignore_index=True), crs=_TARGET_CRS
            )
            combined.to_file(self._dir / "protected_areas.gpkg", driver="GPKG")
            written.append("protected_areas")

        return written

    def load(self) -> ReferenceData:
        loaded: dict[str, object] = {}

        state_boundary_path = self._dir / "state_boundary.gpkg"
        if state_boundary_path.exists():
            gdf = gpd.read_file(state_boundary_path)
            loaded["state_boundary"] = gdf.geometry.iloc[0]

        district_path = self._dir / "district_boundaries.gpkg"
        if district_path.exists():
            gdf = gpd.read_file(district_path)
            crosswalk = self._profile.reference.district_crosswalk or {}
            by_name = dict(zip(gdf["gen"], gdf.geometry, strict=False))
            loaded["district_boundaries"] = {
                code: by_name[name]
                for code, name in crosswalk.items()
                if name in by_name
            }

        protected_areas_path = self._dir / "protected_areas.gpkg"
        if protected_areas_path.exists():
            gdf = gpd.read_file(protected_areas_path)
            loaded["protected_areas"] = list(gdf.geometry)

        return ReferenceData(loaded=loaded)
