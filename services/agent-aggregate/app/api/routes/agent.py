from fastapi import APIRouter, Request

from app.services.agent import AggregateAgent
from shared.rate_limit import enforce_write_rate_limit
from shared.schemas.agents import AggregateAgentRequest, AggregateAgentResponse
from shared.security import require_write_access

router = APIRouter(tags=["agent"])
agent = AggregateAgent()


@router.post("/invoke", response_model=AggregateAgentResponse)
async def invoke(request: AggregateAgentRequest, http_request: Request):
    await require_write_access(http_request)
    await enforce_write_rate_limit(http_request)
    return await agent.execute(request)
