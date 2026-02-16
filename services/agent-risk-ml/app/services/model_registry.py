from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RiskModelArtifact:
    model_version: str
    feature_version: str
    intercept: float
    weights: dict[str, float]


def load_model_artifact(path: str, default_model_version: str) -> RiskModelArtifact:
    file_path = Path(path)
    if not file_path.exists():
        return RiskModelArtifact(
            model_version=default_model_version,
            feature_version="fallback-features-v1",
            intercept=-0.3,
            weights={
                "amount_scaled": 1.0,
                "new_device": 0.5,
                "geo_mismatch": 0.7,
                "high_velocity": 1.0,
                "device_trusted": -0.5,
                "account_age_years": -0.2,
            },
        )

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    weights = {k: float(v) for k, v in dict(raw.get("weights", {})).items()}
    return RiskModelArtifact(
        model_version=str(raw.get("model_version", default_model_version)),
        feature_version=str(raw.get("feature_version", "risk-features-v1")),
        intercept=float(raw.get("intercept", 0.0)),
        weights=weights,
    )
