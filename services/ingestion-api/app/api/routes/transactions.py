import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.repositories.transactions import TransactionRepository
from app.services.publisher import QueuePublisher, get_publisher
from shared.schemas.transactions import TransactionEvent, TransactionIn, TransactionStored

router = APIRouter(tags=["transactions"])
logger = logging.getLogger("ingestion-api")
repo = TransactionRepository()


@router.post("/transactions", response_model=TransactionStored, status_code=status.HTTP_201_CREATED)
async def ingest_transaction(
    payload: TransactionIn,
    publisher: QueuePublisher = Depends(get_publisher),
):
    transaction_id = str(uuid4())
    stored = TransactionStored(
        transaction_id=transaction_id,
        received_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    repo.add(stored)

    event = TransactionEvent(
        event_id=str(uuid4()),
        transaction_id=transaction_id,
        occurred_at=datetime.now(timezone.utc),
        payload=stored,
    )
    await publisher.publish(event)
    logger.info("transaction_ingested", extra={"transaction_id": transaction_id})
    return stored


@router.get("/transactions/{transaction_id}", response_model=TransactionStored)
async def get_transaction(transaction_id: str):
    stored = repo.get(transaction_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return stored
