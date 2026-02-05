from fastapi import APIRouter

from app.services.agent import RiskMLAgent
from shared.schemas.agents import RiskMLAgentRequest, RiskMLAgentResponse

router = APIRouter(tags=["agent"])
agent = RiskMLAgent()


@router.post("/invoke", response_model=RiskMLAgentResponse)
async def invoke(request: RiskMLAgentRequest):
    return await agent.execute(request)
