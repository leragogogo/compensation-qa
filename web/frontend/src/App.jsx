import { useEffect, useState } from 'react'
import './App.css'
import { fetchLands, validate } from './api.js'
import DownloadButtons from './components/DownloadButtons.jsx'
import FindingsTable from './components/FindingsTable.jsx'
import MapView from './components/MapView.jsx'
import SummaryPanel from './components/SummaryPanel.jsx'
import UploadForm from './components/UploadForm.jsx'

export default function App() {
  const [lands, setLands] = useState(['BB'])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [selectedFeatureId, setSelectedFeatureId] = useState(null)

  useEffect(() => {
    fetchLands()
      .then((data) => {
        if (data.land_codes?.length) setLands(data.land_codes)
      })
      .catch(() => setError('Could not reach the API.'))
  }, [])

  async function handleSubmit({ file, state, checkDate, liveRegister }) {
    setLoading(true)
    setError(null)
    setResult(null)
    setSelectedFeatureId(null)
    try {
      setResult(await validate({ file, state, checkDate, liveRegister }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const findingsByFeature = {}
  if (result) {
    for (const finding of result.findings) {
      if (!finding.feature_id) continue
      ;(findingsByFeature[finding.feature_id] ??= []).push(finding)
    }
  }

  return (
    <div className="app">
      <h1>COMPENSATION QA</h1>
      <UploadForm lands={lands} onSubmit={handleSubmit} loading={loading} />
      {error && <div className="error">{error}</div>}
      {result && (
        <>
          <SummaryPanel result={result} />
          <MapView
            map={result.map}
            findingsByFeature={findingsByFeature}
            onSelectFeature={setSelectedFeatureId}
          />
          <DownloadButtons reports={result.reports} landCode={result.land_code} />
          <FindingsTable
            findings={result.findings}
            selectedFeatureId={selectedFeatureId}
            onSelectFeature={setSelectedFeatureId}
          />
        </>
      )}
    </div>
  )
}
