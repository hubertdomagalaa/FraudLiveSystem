from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class LLMExplainerSettings(ServiceSettings):
    service_name: str = "agent-llm-explainer"
    provider: str = "placeholder"
    model: str = "stub-llm"
    prompt_version: str = "v1"
    consumer_group: str = ConsumerGroup.AGENT_EXPLAIN
    consumer_name: str = "agent-llm-explainer-1"
