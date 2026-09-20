import { useEffect, useState } from 'react'
import { fetchReferenceStatus, updateReference } from '../api.js'

function cacheStatusText({ cached, missing }) {
  if (cached.length === 0 && missing.length === 0) {
    return 'No reference datasets configured for this land.'
  }
  if (cached.length === 0) return 'Not cached yet'
  if (missing.length === 0) return `Cached: ${cached.join(', ')}`
  return `Cached: ${cached.join(', ')} · Missing: ${missing.join(', ')}`
}

function cacheStatusClass({ cached, missing }) {
  if (cached.length === 0 && missing.length === 0) return 'cache-status-neutral'
  if (missing.length === 0) return 'cache-status-ok'
  if (cached.length === 0) return 'cache-status-missing'
  return 'cache-status-partial'
}

export default function UploadForm({ lands, onSubmit, loading }) {
  const [file, setFile] = useState(null)
  const [state, setState] = useState(lands[0])
  const [checkDate, setCheckDate] = useState('')
  const [liveRegister, setLiveRegister] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState(null)
  const [cacheStatus, setCacheStatus] = useState(null)

  useEffect(() => {
    let cancelled = false
    setCacheStatus(null)
    fetchReferenceStatus(state)
      .then((result) => {
        if (!cancelled) setCacheStatus(result)
      })
      .catch(() => {
        if (!cancelled) setCacheStatus(null)
      })
    return () => {
      cancelled = true
    }
  }, [state])

  function handleSubmit(event) {
    event.preventDefault()
    if (!file) return
    onSubmit({ file, state, checkDate: checkDate || null, liveRegister })
  }

  async function handleRefreshReference() {
    setRefreshing(true)
    setRefreshError(null)
    try {
      await updateReference(state)
      setCacheStatus(await fetchReferenceStatus(state))
    } catch (err) {
      setRefreshError(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <label>
        Register export (.gpkg)
        <input
          type="file"
          accept=".gpkg"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <label>
        Land
        <select value={state} onChange={(event) => setState(event.target.value)}>
          {lands.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </label>
      <label>
        Check date
        <input
          type="date"
          value={checkDate}
          onChange={(event) => setCheckDate(event.target.value)}
        />
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={liveRegister}
          onChange={(event) => setLiveRegister(event.target.checked)}
        />
        Fetch live EKIS register
      </label>
      <button type="submit" disabled={!file || loading}>
        {loading ? 'Validating…' : 'Validate'}
      </button>
      <div className="reference-refresh">
        <button type="button" onClick={handleRefreshReference} disabled={refreshing}>
          {refreshing ? 'Fetching…' : 'Refresh reference data'}
        </button>
        {cacheStatus && (
          <span className={`cache-status ${cacheStatusClass(cacheStatus)}`}>
            {cacheStatusText(cacheStatus)}
          </span>
        )}
        {refreshError && <span className="refresh-status refresh-status-error">{refreshError}</span>}
      </div>
    </form>
  )
}
