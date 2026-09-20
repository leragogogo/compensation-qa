const SEVERITY_ORDER = { Error: 0, Warning: 1, Info: 2 }

export default function FindingsTable({ findings, selectedFeatureId, onSelectFeature }) {
  const sorted = [...findings].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  )

  return (
    <table className="findings-table">
      <thead>
        <tr>
          <th>Rule</th>
          <th>Severity</th>
          <th>Feature</th>
          <th>Explanation</th>
          <th>Field</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((finding, index) => (
          <tr
            key={index}
            className={[
              `severity-${finding.severity.toLowerCase()}`,
              finding.feature_id && finding.feature_id === selectedFeatureId ? 'selected' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onClick={() => finding.feature_id && onSelectFeature(finding.feature_id)}
          >
            <td>{finding.rule_id}</td>
            <td>
              <span className={`badge badge-${finding.severity.toLowerCase()}`}>
                {finding.severity}
              </span>
            </td>
            <td>{finding.feature_id ?? '—'}</td>
            <td>{finding.explanation}</td>
            <td>{finding.triggered_field ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
