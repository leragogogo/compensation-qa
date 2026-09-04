from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

CRS = "EPSG:25833"

_VALID_POLYGON = Polygon(
    [
        (400100, 5800100),
        (400200, 5800100),
        (400200, 5800200),
        (400100, 5800200),
        (400100, 5800100),
    ]
)


def make_valid_pair() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    intervention = gpd.GeoDataFrame(
        {
            "Eingriff_ID": ["E-1"],
            "Vorhabenskategorie": ["BImSchG"],
            "Vorhabensart": ["Windenergieanlage"],
            "Vorhabensbezeichnung": ["Testvorhaben"],
            "Kategorie_VT": ["Neubau"],
            "Kategorie_ZB": ["Landkreis"],
            "Zulassungsbehoerde": ["Landkreis Potsdam-Mittelmark"],
            "Aktenzeichen_der_Zulassungsbehoerde": ["AZ-2026-001"],
            "Weiteres_Aktenzeichen": [None],
            "Genehmigungsdatum": ["2026-03-01"],
            "Landkreis_oder_kreisfreie_Stadt": ["PM"],
            "Rechtsgrundlage": ["BImSchG"],
            "Kurzbemerkung": [None],
            "geometry": [Point(400050, 5800050)],
        },
        crs=CRS,
    )
    compensation = gpd.GeoDataFrame(
        {
            "Kompensation_ID": ["K-1"],
            "Art_der_Kompensation": ["Realkompensation"],
            "Vorhabensbezeichnung": ["Testvorhaben"],
            "Aktenzeichen_der_Zulassungsbehoerde": ["AZ-2026-001"],
            "Bezeichnung_der_Kompensation": ["Ausgleichsflaeche 1"],
            "Bezeichnung_des_Flaechenpools": [None],
            "Eingriff_ID": [None],
            "geometry": [_VALID_POLYGON],
        },
        crs=CRS,
    )
    return intervention, compensation


def make_orphan_compensation() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    intervention, compensation = make_valid_pair()
    compensation = compensation.copy()
    compensation["Aktenzeichen_der_Zulassungsbehoerde"] = ["AZ-DOES-NOT-EXIST"]
    compensation["Kompensation_ID"] = ["K-orphan"]
    return intervention, compensation


def write_gpkg(
    path: Path, intervention: gpd.GeoDataFrame, compensation: gpd.GeoDataFrame
) -> Path:
    intervention.to_file(path, layer="Eingriff", driver="GPKG")
    compensation.to_file(path, layer="Kompensation", driver="GPKG")
    return path


def write_shapefile_pair(
    dir_path: Path, intervention: gpd.GeoDataFrame, compensation: gpd.GeoDataFrame
) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    intervention.to_file(dir_path / "Eingriff.shp", driver="ESRI Shapefile")
    compensation.to_file(dir_path / "Kompensation.shp", driver="ESRI Shapefile")
    return dir_path


def write_gml_pair(
    dir_path: Path, intervention: gpd.GeoDataFrame, compensation: gpd.GeoDataFrame
) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    intervention.to_file(dir_path / "Eingriff.gml", driver="GML")
    compensation.to_file(dir_path / "Kompensation.gml", driver="GML")
    return dir_path
