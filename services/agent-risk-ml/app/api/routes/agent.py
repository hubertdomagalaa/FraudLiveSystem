from fastapi import APIRouter, Request

from app.services.agent import RiskMLAgent
from shared.rate_limit import enforce_write_rate_limit
from shared.schemas.agents import RiskMLAgentRequest, RiskMLAgentResponse
from shared.security import require_write_access

router = APIRouter(tags=["agent"])
agent = RiskMLAgent()


@router.post("/invoke", response_model=RiskMLAgentResponse)
async def invoke(request: RiskMLAgentRequest, http_request: Request):
    await require_write_access(http_request)
    await enforce_write_rate_limit(http_request)
    return await agent.execute(request)
