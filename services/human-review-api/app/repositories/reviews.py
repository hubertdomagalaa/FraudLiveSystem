import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from shared.schemas.reviews import ReviewAuditEvent, ReviewCaseRecord, ReviewDecisionRecord, ReviewStatus

logger = logging.getLogger("human-review-api")


class ReviewRepository:
    def __init__(self) -> None:
        self._cases: Dict[str, ReviewCaseRecord] = {}
        self._audit: Dict[str, List[ReviewAuditEvent]] = {}

    def add_case(self, case: ReviewCaseRecord) -> None:
        self._cases[case.case_id] = case
        self._add_audit(case.case_id, "CASE_CREATED", {"status": case.status})

    def add_decision(self, case_id: str, decision: ReviewDecisionRecord) -> None:
        case = self._cases[case_id]
        case.decisions.append(decision)
        case.status = ReviewStatus.RESOLVED
        self._add_audit(case_id, "CASE_DECISIONED", {"review_decision_id": decision.review_decision_id})

    def get_case(self, case_id: str) -> Optional[ReviewCaseRecord]:
        return self._cases.get(case_id)

    def get_audit(self, case_id: str) -> List[ReviewAuditEvent]:
        return self._audit.get(case_id, [])

    def _add_audit(self, case_id: str, event_type: str, details: dict) -> None:
        event = ReviewAuditEvent(
            event_id=str(uuid4()),
            case_id=case_id,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            details=details,
        )
        self._audit.setdefault(case_id, []).append(event)
        logger.info("review_audit_event", extra={"case_id": case_id, "event_type": event_type})
