from typing import Dict, Optional

from shared.schemas.transactions import TransactionStored


class TransactionRepository:
    def __init__(self) -> None:
        self._store: Dict[str, TransactionStored] = {}

    def add(self, transaction: TransactionStored) -> None:
        self._store[transaction.transaction_id] = transaction

    def get(self, transaction_id: str) -> Optional[TransactionStored]:
        return self._store.get(transaction_id)
