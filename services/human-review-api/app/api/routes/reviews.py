from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.repositories.reviews import ReviewRepository
from shared.schemas.reviews import (
    ReviewAuditEvent,
    ReviewCaseIn,
    ReviewCaseRecord,
    ReviewDecisionIn,
    ReviewDecisionRecord,
    ReviewStatus,
)

router = APIRouter(tags=["reviews"])
repo = ReviewRepository()


@router.post("/cases", response_model=ReviewCaseRecord, status_code=status.HTTP_201_CREATED)
async def create_case(payload: ReviewCaseIn):
    case = ReviewCaseRecord(
        case_id=str(uuid4()),
        status=ReviewStatus.OPEN,
        created_at=datetime.now(timezone.utc),
        transaction_id=payload.transaction_id,
        decision_id=payload.decision_id,
        reason=payload.reason,
        payload=payload.payload,
    )
    repo.add_case(case)
    return case


@router.get("/cases/{case_id}", response_model=ReviewCaseRecord)
async def get_case(case_id: str):
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/cases/{case_id}/decision", response_model=ReviewDecisionRecord, status_code=status.HTTP_201_CREATED)
async def add_decision(case_id: str, payload: ReviewDecisionIn):
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    decision = ReviewDecisionRecord(
        review_decision_id=str(uuid4()),
        decided_at=datetime.now(timezone.utc),
        reviewer_id=payload.reviewer_id,
        outcome=payload.outcome,
        comment=payload.comment,
        labels=payload.labels,
    )
    repo.add_decision(case_id, decision)
    return decision


@router.get("/cases/{case_id}/audit", response_model=list[ReviewAuditEvent])
async def get_audit(case_id: str):
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return repo.get_audit(case_id)
