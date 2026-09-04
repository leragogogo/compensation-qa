from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from shapely.geometry.base import BaseGeometry


class Severity(str, Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"


@dataclass(slots=True)
class InterventionFeature:
    intervention_id: str | None
    geometry: BaseGeometry
    project_category: str | None = None
    project_type: str | None = None
    project_name: str | None = None
    category_vt: str | None = None
    category_zb: str | None = None
    approval_authority: str | None = None
    case_reference: str | None = None
    additional_case_reference: str | None = None
    approval_date: date | None = None
    district: str | None = None
    legal_basis: str | None = None
    remarks: str | None = None
    # Profile-specific attributes (e.g. a field only one land's register captures).
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompensationFeature:
    compensation_id: str | None
    geometry: BaseGeometry
    compensation_type: str | None = None
    project_name: str | None = None
    case_reference: str | None = None
    compensation_name: str | None = None
    area_pool_name: str | None = None
    intervention_id: str | None = None
    linked_intervention: InterventionFeature | None = None
    # Profile-specific attributes (e.g. a field only one land's register captures).
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Finding:
    """One rule's verdict on one feature."""

    rule_id: str
    severity: Severity
    feature_id: str | None
    land_code: str
    explanation: str
    triggered_field: str | None = None
    observed_value: str | None = None
