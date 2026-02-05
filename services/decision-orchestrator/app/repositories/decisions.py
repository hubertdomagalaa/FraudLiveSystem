from typing import Dict, Optional

from shared.schemas.decisions import DecisionAggregate


class DecisionRepository:
    def __init__(self) -> None:
        self._store: Dict[str, DecisionAggregate] = {}

    def add(self, decision: DecisionAggregate) -> None:
        self._store[decision.decision_id] = decision

    def get(self, decision_id: str) -> Optional[DecisionAggregate]:
        return self._store.get(decision_id)
