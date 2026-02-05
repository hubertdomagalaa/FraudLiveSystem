from fastapi import APIRouter

from app.services.agent import PolicyAgent
from shared.schemas.agents import PolicyAgentRequest, PolicyAgentResponse

router = APIRouter(tags=["agent"])
agent = PolicyAgent()


@router.post("/invoke", response_model=PolicyAgentResponse)
async def invoke(request: PolicyAgentRequest):
    return await agent.execute(request)
