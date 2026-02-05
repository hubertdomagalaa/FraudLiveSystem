from fastapi import APIRouter

from app.services.agent import LLMExplanationAgent
from shared.schemas.agents import LLMExplanationRequest, LLMExplanationResponse

router = APIRouter(tags=["agent"])
agent = LLMExplanationAgent()


@router.post("/invoke", response_model=LLMExplanationResponse)
async def invoke(request: LLMExplanationRequest):
    return await agent.execute(request)
