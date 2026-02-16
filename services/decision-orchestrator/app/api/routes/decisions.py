from fastapi import APIRouter, HTTPException, Query, Request

from shared.database import PlatformDatabase

router = APIRouter(tags=["orchestration"])


def _db(request: Request) -> PlatformDatabase:
    return request.app.state.db


@router.get("/cases")
async def list_cases(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    return await _db(request).list_cases(limit=limit)


@router.get("/cases/{case_id}/events")
async def case_events(case_id: str, request: Request):
    case = await _db(request).get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _db(request).list_case_events(case_id)


@router.get("/cases/{case_id}/agent-runs")
async def case_agent_runs(case_id: str, request: Request):
    case = await _db(request).get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _db(request).list_agent_runs(case_id)


@router.get("/cases/{case_id}/decisions")
async def case_decisions(case_id: str, request: Request):
    case = await _db(request).get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _db(request).list_decisions(case_id)


@router.get("/cases/{case_id}/reviews")
async def case_reviews(case_id: str, request: Request):
    case = await _db(request).get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return await _db(request).list_human_review_actions(case_id)
