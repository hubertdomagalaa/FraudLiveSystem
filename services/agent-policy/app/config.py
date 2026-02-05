from shared.config import ServiceSettings


class PolicySettings(ServiceSettings):
    service_name: str = "agent-policy"
    ruleset_version: str = "v0"
