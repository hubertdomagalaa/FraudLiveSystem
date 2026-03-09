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
    merchant_risk_review_gte: float
    chargeback_review_amount_gte: float
    block_high_risk_country_new_device_risk_gte: float
    reason_block_risk: str
    reason_review_risk: str
    reason_review_amount: str
    reason_review_merchant_risk: str
    reason_review_chargeback_amount: str
    reason_review_geo_device: str
    reason_block_geo_device: str


def load_ruleset(path: str, default_ruleset_version: str) -> PolicyRuleset:
    file_path = Path(path)
    if not file_path.exists():
        return PolicyRuleset(
            ruleset_version=default_ruleset_version,
            block_risk_score_gte=0.9,
            review_risk_score_gte=0.6,
            review_amount_gte=5000.0,
            merchant_risk_review_gte=0.75,
            chargeback_review_amount_gte=1000.0,
            block_high_risk_country_new_device_risk_gte=0.85,
            reason_block_risk="RISK_SCORE_CRITICAL",
            reason_review_risk="RISK_SCORE_HIGH",
            reason_review_amount="HIGH_AMOUNT",
            reason_review_merchant_risk="MERCHANT_RISK_HIGH",
            reason_review_chargeback_amount="CHARGEBACK_HISTORY_WITH_HIGH_AMOUNT",
            reason_review_geo_device="HIGH_RISK_COUNTRY_NEW_DEVICE",
            reason_block_geo_device="HIGH_RISK_COUNTRY_NEW_DEVICE_CRITICAL",
        )

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    thresholds = dict(raw.get("thresholds", {}))
    reason_codes = dict(raw.get("reason_codes", {}))
    return PolicyRuleset(
        ruleset_version=str(raw.get("ruleset_version", default_ruleset_version)),
        block_risk_score_gte=float(thresholds.get("block_risk_score_gte", 0.9)),
        review_risk_score_gte=float(thresholds.get("review_risk_score_gte", 0.6)),
        review_amount_gte=float(thresholds.get("review_amount_gte", 5000.0)),
        merchant_risk_review_gte=float(thresholds.get("merchant_risk_review_gte", 0.75)),
        chargeback_review_amount_gte=float(thresholds.get("chargeback_review_amount_gte", 1000.0)),
        block_high_risk_country_new_device_risk_gte=float(
            thresholds.get("block_high_risk_country_new_device_risk_gte", 0.85)
        ),
        reason_block_risk=str(reason_codes.get("block_risk", "RISK_SCORE_CRITICAL")),
        reason_review_risk=str(reason_codes.get("review_risk", "RISK_SCORE_HIGH")),
        reason_review_amount=str(reason_codes.get("review_amount", "HIGH_AMOUNT")),
        reason_review_merchant_risk=str(reason_codes.get("review_merchant_risk", "MERCHANT_RISK_HIGH")),
        reason_review_chargeback_amount=str(
            reason_codes.get("review_chargeback_amount", "CHARGEBACK_HISTORY_WITH_HIGH_AMOUNT")
        ),
        reason_review_geo_device=str(reason_codes.get("review_geo_device", "HIGH_RISK_COUNTRY_NEW_DEVICE")),
        reason_block_geo_device=str(
            reason_codes.get("block_geo_device", "HIGH_RISK_COUNTRY_NEW_DEVICE_CRITICAL")
        ),
    )
