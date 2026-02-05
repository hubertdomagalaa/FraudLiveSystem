from fastapi import APIRouter

from app.services.agent import ContextAgent
from shared.schemas.agents import ContextAgentRequest, ContextAgentResponse

router = APIRouter(tags=["agent"])
agent = ContextAgent()


@router.post("/invoke", response_model=ContextAgentResponse)
async def invoke(request: ContextAgentRequest):
    return await agent.execute(request)
