"""Lightweight domain models for multi-company teams."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Company:
    id: str
    name: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class User:
    id: str
    company_id: str
    name: str
    role: str = "member"  # owner | admin | member
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimeSlot:
    """A bookable work block owned by a user."""

    id: str
    company_id: str
    owner_id: str
    start_at: str  # ISO local datetime YYYY-MM-DDTHH:MM
    end_at: str
    title: str
    status: str = "free"  # free | booked | busy
    booker_id: str | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressUpdate:
    id: str
    company_id: str
    author_id: str
    title: str
    body: str
    percent: int = 0  # 0-100
    created_at: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModuleState:
    name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
