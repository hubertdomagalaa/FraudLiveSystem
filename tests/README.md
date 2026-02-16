# Tests

Current baseline:
- `tests/test_events.py` - shared event helper tests.
- `services/*/tests` - service-level unit/integration tests.

Run shared tests:
```bash
PYTHONPATH=libs/shared pytest -q tests
```

Run service tests (example):
```bash
PYTHONPATH="libs/shared:services/ingestion-api" pytest -q services/ingestion-api/tests
```
