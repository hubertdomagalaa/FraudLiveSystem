from fastapi import APIRouter, Request

from app.services.agent import PolicyAgent
from shared.rate_limit import enforce_write_rate_limit
from shared.schemas.agents import PolicyAgentRequest, PolicyAgentResponse
from shared.security import require_write_access

router = APIRouter(tags=["agent"])
agent = PolicyAgent()


@router.post("/invoke", response_model=PolicyAgentResponse)
async def invoke(request: PolicyAgentRequest, http_request: Request):
    await require_write_access(http_request)
    await enforce_write_rate_limit(http_request)
    return await agent.execute(request)
