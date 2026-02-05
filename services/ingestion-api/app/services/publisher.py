import logging
from typing import Protocol

from app.config import IngestionSettings
from shared.schemas.transactions import TransactionEvent

logger = logging.getLogger("ingestion-api")
settings = IngestionSettings()


class QueuePublisher(Protocol):
    async def publish(self, event: TransactionEvent) -> None:
        ...


class NoOpQueuePublisher:
    async def publish(self, event: TransactionEvent) -> None:
        logger.info(
            "queue_publish_noop",
            extra={"event_id": event.event_id, "transaction_id": event.transaction_id},
        )


def get_publisher() -> QueuePublisher:
    return NoOpQueuePublisher()
