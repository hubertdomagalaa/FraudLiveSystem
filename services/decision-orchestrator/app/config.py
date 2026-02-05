from shared.config import ServiceSettings


class OrchestratorSettings(ServiceSettings):
    service_name: str = "decision-orchestrator"
    context_agent_url: str = "http://agent-context:8000"
    risk_agent_url: str = "http://agent-risk-ml:8000"
    policy_agent_url: str = "http://agent-policy:8000"
    llm_agent_url: str = "http://agent-llm-explainer:8000"
    default_decision: str = "REVIEW"
