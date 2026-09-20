import { useMemo } from 'react'
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const STATUS_COLOR = {
  Error: '#9c3b2c',
  Warning: '#a9691f',
  OK: '#3c6e58',
}

function styleFor(feature) {
  const color = STATUS_COLOR[feature.properties.qa_status] ?? '#56625a'
  return { color, weight: 2, fillColor: color, fillOpacity: 0.35 }
}

export default function MapView({ map, findingsByFeature, onSelectFeature }) {
  const bounds = useMemo(() => computeBounds(map), [map])

  function onEachFeature(feature, layer) {
    const featureId = feature.properties.feature_id
    layer.on('click', () => onSelectFeature(featureId))
    const matches = findingsByFeature[featureId] ?? []
    const items = matches
      .map((finding) => `<li>${finding.rule_id} — ${finding.explanation}</li>`)
      .join('')
    layer.bindPopup(`<b>${featureId}</b>${items ? `<ul>${items}</ul>` : '<br/>No findings.'}`)
  }

  if (!bounds) {
    return <div className="map-view map-view-empty">No geometry to display.</div>
  }

  return (
    <MapContainer bounds={bounds} className="map-view" scrollWheelZoom>
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON data={map.kompensation} style={styleFor} onEachFeature={onEachFeature} />
      <GeoJSON data={map.eingriff} style={styleFor} onEachFeature={onEachFeature} />
    </MapContainer>
  )
}

function computeBounds(map) {
  const coords = []
  for (const collection of [map.kompensation, map.eingriff]) {
    for (const feature of collection.features) {
      collectCoords(feature.geometry, coords)
    }
  }
  if (!coords.length) return null
  const lats = coords.map((c) => c[1])
  const lons = coords.map((c) => c[0])
  return [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ]
}

function collectCoords(geometry, out) {
  if (!geometry) return
  const { type, coordinates } = geometry
  if (type === 'Point') out.push(coordinates)
  else if (type === 'MultiPoint' || type === 'LineString') coordinates.forEach((c) => out.push(c))
  else if (type === 'Polygon' || type === 'MultiLineString')
    coordinates.forEach((ring) => ring.forEach((c) => out.push(c)))
  else if (type === 'MultiPolygon')
    coordinates.forEach((polygon) => polygon.forEach((ring) => ring.forEach((c) => out.push(c))))
}
