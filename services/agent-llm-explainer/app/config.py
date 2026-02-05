from shared.config import ServiceSettings


class LLMExplainerSettings(ServiceSettings):
    service_name: str = "agent-llm-explainer"
    provider: str = "placeholder"
    model: str = "stub-llm"
    prompt_version: str = "v0"
