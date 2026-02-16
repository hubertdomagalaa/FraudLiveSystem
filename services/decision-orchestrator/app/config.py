from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class OrchestratorSettings(ServiceSettings):
    service_name: str = "decision-orchestrator"
    consumer_group: str = ConsumerGroup.ORCHESTRATOR
    consumer_name: str = "decision-orchestrator-1"
