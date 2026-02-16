from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class ContextSettings(ServiceSettings):
    service_name: str = "agent-context"
    consumer_group: str = ConsumerGroup.AGENT_CONTEXT
    consumer_name: str = "agent-context-1"
