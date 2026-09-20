export default function SummaryPanel({ result }) {
  const { land_code, check_date, register_fetch_timestamp, live_register_skipped, summary, findings } =
    result

  return (
    <div className="summary-panel">
      <div>
        <span className="label">Land</span> {land_code}
      </div>
      <div>
        <span className="label">Check date</span> {check_date}
      </div>
      <div>
        <span className="label">Register fetch</span> {register_fetch_timestamp ?? 'not run'}
      </div>
      {live_register_skipped && (
        <div className="notice">Live register requested but not configured for this land.</div>
      )}
      <div className="counts">
        <span className="badge badge-error">{summary.error} error(s)</span>
        <span className="badge badge-warning">{summary.warning} warning(s)</span>
        <span className="badge badge-info">{summary.info} info</span>
        <span className="total">{findings.length} finding(s) total</span>
      </div>
    </div>
  )
}
