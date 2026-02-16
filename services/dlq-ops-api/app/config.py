from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class DlqOpsSettings(ServiceSettings):
    service_name: str = "dlq-ops-api"
    consumer_group: str = ConsumerGroup.DLQ_OPS
    consumer_name: str = "dlq-ops-api-1"
