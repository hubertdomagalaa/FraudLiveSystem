from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class PolicySettings(ServiceSettings):
    service_name: str = "agent-policy"
    ruleset_version: str = "v2"
    ruleset_path: str = "app/rules/ruleset_v2.json"
    consumer_group: str = ConsumerGroup.AGENT_POLICY
    consumer_name: str = "agent-policy-1"
