from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import BaseSchema


class ReviewStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class ReviewDecisionOutcome(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class ReviewCaseIn(BaseSchema):
    transaction_id: str
    decision_id: Optional[str] = None
    reason: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ReviewDecisionIn(BaseSchema):
    reviewer_id: str
    outcome: ReviewDecisionOutcome
    comment: Optional[str] = None
    labels: List[str] = Field(default_factory=list)


class ReviewDecisionRecord(ReviewDecisionIn):
    review_decision_id: str
    decided_at: datetime


class ReviewCaseRecord(BaseSchema):
    case_id: str
    status: ReviewStatus
    created_at: datetime
    transaction_id: str
    decision_id: Optional[str] = None
    reason: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    decisions: List[ReviewDecisionRecord] = Field(default_factory=list)


class ReviewAuditEvent(BaseSchema):
    event_id: str
    case_id: str
    event_type: str
    occurred_at: datetime
    details: Dict[str, Any] = Field(default_factory=dict)
