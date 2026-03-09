"""Dev/demo helper for seeding deterministic ALLOW/BLOCK/REVIEW cases via ingestion API."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import request


@dataclass(frozen=True)
class DemoScenario:
    name: str
    idempotency_suffix: str
    payload: dict


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_demo_scenarios() -> list[DemoScenario]:
    timestamp = iso_now()
    return [
        DemoScenario(
            name="ALLOW",
            idempotency_suffix="allow",
            payload={
                "amount": 180.0,
                "currency": "USD",
                "merchant_id": "merchant-demo-allow",
                "card_id": "card-demo-allow",
                "timestamp": timestamp,
                "country": "US",
                "ip": "198.51.100.20",
                "device_id": "dev-demo-known",
                "prior_chargeback_flags": False,
                "merchant_risk_score": 0.12,
                "metadata": {"device_trust": "trusted", "account_age_days": 500, "new_device": False},
            },
        ),
        DemoScenario(
            name="REVIEW",
            idempotency_suffix="review",
            payload={
                "amount": 4200.0,
                "currency": "USD",
                "merchant_id": "merchant-demo-review",
                "card_id": "card-demo-review",
                "timestamp": timestamp,
                "country": "ID",
                "ip": "203.0.113.55",
                "device_id": "dev-demo-review",
                "prior_chargeback_flags": False,
                "merchant_risk_score": 0.62,
                "metadata": {"device_trust": "unverified", "new_device": True, "account_age_days": 5},
            },
        ),
        DemoScenario(
            name="BLOCK",
            idempotency_suffix="block",
            payload={
                "amount": 22000.0,
                "currency": "USD",
                "merchant_id": "merchant-demo-block",
                "card_id": "card-demo-block",
                "timestamp": timestamp,
                "country": "NG",
                "ip": "203.0.113.80",
                "device_id": "dev-demo-high-risk",
                "prior_chargeback_flags": True,
                "merchant_risk_score": 0.95,
                "metadata": {"device_trust": "unverified", "new_device": True, "high_velocity": True, "account_age_days": 1},
            },
        ),
    ]


def post_transaction(base_url: str, token: str, idempotency_key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=f"{base_url.rstrip('/')}/v1/transactions",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": idempotency_key,
        },
    )
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo transactions for ALLOW/BLOCK/REVIEW scenarios.")
    parser.add_argument("--base-url", default="http://localhost:8001", help="Ingestion API base URL")
    parser.add_argument("--token", required=True, help="Bearer token with fraud.write scope")
    parser.add_argument("--prefix", default="demo-seed", help="Idempotency key prefix")
    args = parser.parse_args()

    run_id = uuid.uuid4().hex[:8]
    print(f"[demo-seed] run_id={run_id}")

    for scenario in build_demo_scenarios():
        idempotency_key = f"{args.prefix}-{run_id}-{scenario.idempotency_suffix}"
        result = post_transaction(args.base_url, args.token, idempotency_key, scenario.payload)
        print(
            json.dumps(
                {
                    "scenario": scenario.name,
                    "idempotency_key": idempotency_key,
                    "transaction_id": result.get("transaction_id"),
                    "merchant_id": scenario.payload["merchant_id"],
                    "amount": scenario.payload["amount"],
                }
            )
        )


if __name__ == "__main__":
    main()
