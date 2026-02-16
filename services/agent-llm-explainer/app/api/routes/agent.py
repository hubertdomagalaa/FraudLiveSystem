from fastapi import APIRouter, Request

from app.services.agent import LLMExplanationAgent
from shared.rate_limit import enforce_write_rate_limit
from shared.schemas.agents import LLMExplanationRequest, LLMExplanationResponse
from shared.security import require_write_access

router = APIRouter(tags=["agent"])
agent = LLMExplanationAgent()


@router.post("/invoke", response_model=LLMExplanationResponse)
async def invoke(request: LLMExplanationRequest, http_request: Request):
    await require_write_access(http_request)
    await enforce_write_rate_limit(http_request)
    return await agent.execute(request)
