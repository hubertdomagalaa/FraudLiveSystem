import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_demo_seed_contains_allow_review_block() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "demo_seed.py"
    spec = spec_from_file_location("demo_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules["demo_seed"] = module
    spec.loader.exec_module(module)

    scenarios = module.build_demo_scenarios()
    names = [scenario.name for scenario in scenarios]

    assert names == ["ALLOW", "REVIEW", "BLOCK"]
    assert all("merchant_risk_score" in scenario.payload for scenario in scenarios)
    assert all("country" in scenario.payload for scenario in scenarios)
