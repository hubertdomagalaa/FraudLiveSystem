from fastapi import APIRouter, Request

from app.services.agent import ContextAgent
from shared.rate_limit import enforce_write_rate_limit
from shared.schemas.agents import ContextAgentRequest, ContextAgentResponse
from shared.security import require_write_access

router = APIRouter(tags=["agent"])
agent = ContextAgent()


@router.post("/invoke", response_model=ContextAgentResponse)
async def invoke(request: ContextAgentRequest, http_request: Request):
    await require_write_access(http_request)
    await enforce_write_rate_limit(http_request)
    return await agent.execute(request)
