from shared.config import ServiceSettings


class RiskMLSettings(ServiceSettings):
    service_name: str = "agent-risk-ml"
    model_version: str = "stub-0.1"
    default_risk_score: float = 0.42
