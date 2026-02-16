from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PolicyRuleset:
    ruleset_version: str
    block_risk_score_gte: float
    review_risk_score_gte: float
    review_amount_gte: float
    reason_block_risk: str
    reason_review_risk: str
    reason_review_amount: str


def load_ruleset(path: str, default_ruleset_version: str) -> PolicyRuleset:
    file_path = Path(path)
    if not file_path.exists():
        return PolicyRuleset(
            ruleset_version=default_ruleset_version,
            block_risk_score_gte=0.9,
            review_risk_score_gte=0.6,
            review_amount_gte=5000.0,
            reason_block_risk="RISK_SCORE_CRITICAL",
            reason_review_risk="RISK_SCORE_HIGH",
            reason_review_amount="HIGH_AMOUNT",
        )

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    thresholds = dict(raw.get("thresholds", {}))
    reason_codes = dict(raw.get("reason_codes", {}))
    return PolicyRuleset(
        ruleset_version=str(raw.get("ruleset_version", default_ruleset_version)),
        block_risk_score_gte=float(thresholds.get("block_risk_score_gte", 0.9)),
        review_risk_score_gte=float(thresholds.get("review_risk_score_gte", 0.6)),
        review_amount_gte=float(thresholds.get("review_amount_gte", 5000.0)),
        reason_block_risk=str(reason_codes.get("block_risk", "RISK_SCORE_CRITICAL")),
        reason_review_risk=str(reason_codes.get("review_risk", "RISK_SCORE_HIGH")),
        reason_review_amount=str(reason_codes.get("review_amount", "HIGH_AMOUNT")),
    )
