const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function fetchLands() {
  const res = await fetch(`${API_BASE}/api/lands`)
  if (!res.ok) throw new Error('Could not load lands.')
  return res.json()
}

export async function validate({ file, state, checkDate, liveRegister }) {
  const form = new FormData()
  form.append('file', file)
  form.append('state', state)
  if (checkDate) form.append('check_date', checkDate)
  if (liveRegister) form.append('live_register', 'true')

  const res = await fetch(`${API_BASE}/api/validate`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function fetchReferenceStatus(state) {
  const res = await fetch(
    `${API_BASE}/api/reference/status?state=${encodeURIComponent(state)}`,
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export async function updateReference(state) {
  const res = await fetch(
    `${API_BASE}/api/reference/update?state=${encodeURIComponent(state)}`,
    { method: 'POST' },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}
