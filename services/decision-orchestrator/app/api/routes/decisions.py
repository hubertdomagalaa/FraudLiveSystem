from fastapi import APIRouter, HTTPException, status

from app.config import OrchestratorSettings
from app.orchestration.client import AgentClient
from app.orchestration.state_machine import DecisionStateMachine
from app.repositories.decisions import DecisionRepository
from shared.schemas.decisions import DecisionAggregate, DecisionRequest

router = APIRouter(tags=["decisions"])
settings = OrchestratorSettings()
repo = DecisionRepository()
client = AgentClient(settings)
orchestrator = DecisionStateMachine(client, settings)


@router.post("/decisions", response_model=DecisionAggregate, status_code=status.HTTP_201_CREATED)
async def create_decision(request: DecisionRequest):
    decision = await orchestrator.run(request.transaction)
    repo.add(decision)
    return decision


@router.get("/decisions/{decision_id}", response_model=DecisionAggregate)
async def get_decision(decision_id: str):
    decision = repo.get(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision
