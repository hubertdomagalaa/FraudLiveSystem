from shared.config import ServiceSettings
from shared.events import ConsumerGroup


class RiskMLSettings(ServiceSettings):
    service_name: str = "agent-risk-ml"
    model_version: str = "stub-0.1"
    model_artifact_path: str = "app/assets/model_stub_v1.json"
    default_risk_score: float = 0.42
    consumer_group: str = ConsumerGroup.AGENT_RISK
    consumer_name: str = "agent-risk-ml-1"
