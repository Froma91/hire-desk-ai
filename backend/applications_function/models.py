"""Domain models for PROJECT_HIRE_DESK_AI — ApplicationsFunction."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class Status(str, Enum):
    WISHLIST   = "Wishlist"
    APPLIED    = "Applied"
    INTERVIEW  = "Interview"
    OFFER      = "Offer"
    REJECTED   = "Rejected"


class Priority(str, Enum):
    HIGH   = "High"
    MEDIUM = "Medium"
    LOW    = "Low"


@dataclass
class StatusEntry:
    status: Status
    timestamp: datetime


@dataclass
class NextAction:
    label: str
    priority: Priority
    explanation: Optional[str] = None   # ≤ 280 chars; None when Bedrock unavailable


@dataclass
class Application:
    userId: str
    applicationId: str
    jobTitle: str
    status: Status
    createdAt: datetime
    updatedAt: datetime
    company: Optional[str] = None
    location: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    experienceLevel: Optional[str] = None
    statusHistory: list[StatusEntry] = field(default_factory=list)
    nextAction: Optional[NextAction] = None


@dataclass
class ExtractionResult:
    jobTitle: Optional[str]
    company: Optional[str]
    location: Optional[str]
    skills: list[str]
    responsibilities: list[str]
    languages: list[str]
    experienceLevel: Optional[str]


@dataclass
class DashboardStats:
    total: int
    byStatus: dict[str, int]
    currentWeek: int
