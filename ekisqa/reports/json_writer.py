from __future__ import annotations

import json
from dataclasses import asdict

from ekisqa.model import Finding
from ekisqa.reports.metadata import ReportMetadata


def _finding_to_dict(finding: Finding) -> dict:
    data = asdict(finding)
    data["severity"] = finding.severity.value
    return data


def write_json(findings: list[Finding], metadata: ReportMetadata) -> str:
    payload = {
        "land_code": metadata.land_code,
        "check_date": metadata.check_date.isoformat(),
        "register_fetch_timestamp": (
            metadata.register_fetch_timestamp.isoformat()
            if metadata.register_fetch_timestamp
            else None
        ),
        "findings": [_finding_to_dict(f) for f in findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
