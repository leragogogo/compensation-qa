from __future__ import annotations

from collections.abc import Iterable
from html import escape

from ekisqa.model import Finding, Severity
from ekisqa.reports.metadata import ReportMetadata, index_rules
from ekisqa.rules.base import Rule

_SEVERITY_ORDER = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}

_STYLE = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       margin: 0; padding: 2rem; background: #f7f7f5; color: #1a1a1a; }
h1 { font-size: 1.4rem; margin: 0 0 0.5rem; }
.meta { color: #555; font-size: 0.9rem; margin-bottom: 1.5rem; }
.meta span { margin-right: 1.5rem; }
table { border-collapse: collapse; width: 100%; background: #fff; }
th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #ddd;
         vertical-align: top; font-size: 0.9rem; }
th { background: #eee; }
tr.severity-error { border-left: 4px solid #9c3b2c; }
tr.severity-warning { border-left: 4px solid #a9691f; }
tr.severity-info { border-left: 4px solid #3f6684; }
.badge { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 3px;
         font-size: 0.8rem; font-weight: 600; color: #fff; }
.badge-error { background: #9c3b2c; }
.badge-warning { background: #a9691f; }
.badge-info { background: #3f6684; }
.empty { padding: 2rem; text-align: center; color: #555; }
"""

_BADGE_CLASS = {
    Severity.ERROR: "badge-error",
    Severity.WARNING: "badge-warning",
    Severity.INFO: "badge-info",
}

_ROW_CLASS = {
    Severity.ERROR: "severity-error",
    Severity.WARNING: "severity-warning",
    Severity.INFO: "severity-info",
}


def _sort_key(finding: Finding) -> tuple:
    return (
        _SEVERITY_ORDER.get(finding.severity, 99),
        finding.rule_id,
        finding.feature_id or "",
    )


def _row_html(finding: Finding, rule: Rule | None) -> str:
    scope = rule.scope if rule is not None else "?"
    return f"""
    <tr class="{_ROW_CLASS.get(finding.severity, "")}">
      <td>{escape(finding.rule_id)}</td>
      <td><span class="badge {_BADGE_CLASS.get(finding.severity, "")}">{escape(finding.severity.value)}</span></td>
      <td>{escape(scope)}</td>
      <td>{escape(finding.feature_id or "—")}</td>
      <td>{escape(finding.explanation)}</td>
      <td>{escape(finding.triggered_field or "—")}{
        f" = {escape(str(finding.observed_value))}" if finding.observed_value is not None else ""
      }</td>
    </tr>"""


def write_html(
    findings: list[Finding],
    rules: Iterable[Rule],
    metadata: ReportMetadata,
) -> str:
    rule_index = index_rules(rules)
    sorted_findings = sorted(findings, key=_sort_key)

    register_line = (
        f"<span>Register fetched: {escape(metadata.register_fetch_timestamp.isoformat())}</span>"
        if metadata.register_fetch_timestamp
        else "<span>Register fetch: not run</span>"
    )

    if sorted_findings:
        rows = "\n".join(
            _row_html(finding, rule_index.get(finding.rule_id))
            for finding in sorted_findings
        )
        body = f"""
    <table>
      <thead>
        <tr>
          <th>Rule</th><th>Severity</th><th>Scope</th><th>Feature</th>
          <th>Explanation</th><th>Triggered field</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>"""
    else:
        body = '<div class="empty">No findings.</div>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EKIS QA Report — {escape(metadata.land_code)}</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>EKIS QA Report</h1>
<div class="meta">
  <span>Land: {escape(metadata.land_code)}</span>
  <span>Check date: {escape(metadata.check_date.isoformat())}</span>
  {register_line}
  <span>Findings: {len(findings)}</span>
</div>
{body}
</body>
</html>"""
