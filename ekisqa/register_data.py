from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shapely.strtree import STRtree

from ekisqa.model import CompensationFeature


@dataclass(frozen=True, slots=True)
class ReferenceData:
    loaded: dict[str, Any] = field(default_factory=dict)

    def has(self, name: str) -> bool:
        return name in self.loaded


@dataclass(slots=True)
class RegisterSnapshot:
    land_code: str
    features: list[CompensationFeature]
    fetch_timestamp: datetime
    index: STRtree | None = None
