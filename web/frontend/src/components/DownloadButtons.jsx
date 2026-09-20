function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function base64ToBytes(base64) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

export default function DownloadButtons({ reports, landCode }) {
  return (
    <div className="download-buttons">
      <button
        onClick={() =>
          downloadBlob(
            `${landCode}-report.html`, 
            new Blob([reports.html], { type: 'text/html' })
          )
        }
      >
        Download HTML
      </button>
      <button
        onClick={() =>
          downloadBlob(
            `${landCode}-report.gpkg`,
            new Blob([base64ToBytes(reports.gpkg_base64)], {
              type: 'application/geopackage+sqlite3',
            }),
          )
        }
      >
        Download GeoPackage
      </button>
      <button
        onClick={() =>
          downloadBlob(
            `${landCode}-kompensation.geojson`,
            new Blob([reports.geojson.kompensation], { type: 'application/geo+json' }),
          )
        }
      >
        Download Kompensation GeoJSON
      </button>
      <button
        onClick={() =>
          downloadBlob(
            `${landCode}-eingriff.geojson`,
            new Blob([reports.geojson.eingriff], { type: 'application/geo+json' }),
          )
        }
      >
        Download Eingriff GeoJSON
      </button>
    </div>
  )
}
