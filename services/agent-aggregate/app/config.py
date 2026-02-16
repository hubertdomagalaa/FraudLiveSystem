from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class AggregateSettings(ServiceSettings):
    service_name: str = "agent-aggregate"
    consumer_group: str = ConsumerGroup.AGENT_AGGREGATE
    consumer_name: str = "agent-aggregate-1"
