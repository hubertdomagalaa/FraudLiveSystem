# DEMO SCRIPT - Fraud Decision Support Platform

Ten skrypt jest zaprojektowany na 5 minut live demo.

## 0. Setup (30-60s)

1. Uruchom backend + UI zgodnie z `README.md`.
2. Wygeneruj token JWT (`fraud.write`) i wklej do pola Bearer Token w UI.
3. Opcjonalnie zasil scenariusze demo helperem:

```bash
python scripts/demo_seed.py --token <JWT_TOKEN>
```

## 1. Create Transaction z UI (60s)

1. W sekcji `Create Transaction` kliknij preset `Needs Review Demo`.
2. Kliknij `Create transaction`.
3. Poka¿, ¿e nowy case pojawia siê od razu na liœcie i jest zaznaczony.

Co powiedzieæ:
- "Tworzenie case dzia³a bezpoœrednio z UI i zapisuje transakcjê przez ingestion API."
- "Idempotency-Key jest generowany po stronie UI, a backend trzyma kontrakt eventowy `case.created`."

## 2. Pipeline Status + Why this decision? (60-90s)

1. Otwórz szczegó³y case.
2. Poka¿ `Pipeline Status`:
   - `INGESTED`
   - `CONTEXT_DONE`
   - `RISK_DONE`
   - `POLICY_DONE`
   - `EXPLAIN_DONE`
   - `AGGREGATED`
   - `REVIEW_REQUIRED` (dla scenariusza review)
   - `FINALIZED` po zamkniêciu
3. Poka¿ `Why this decision?`:
   - Signals
   - Risk Score
   - Policy Violations
   - Recommendation
   - Explanation

Co powiedzieæ:
- "Statusy s¹ wyliczane wy³¹cznie z istniej¹cych eventów i decyzji, bez ukrytego stanu."
- "Wyjaœnienie decyzji jest czytelne operacyjnie, bez koniecznoœci czytania surowego JSON."

## 3. REVIEW + human decision (60-90s)

1. Wybierz case z `REVIEW`.
2. W panelu `Manual Review` wyœlij decyzjê (`ALLOW` albo `BLOCK`).
3. Poka¿ wpisy w `Review Actions` i finalny wpis w `Decisions`.
4. Zwróæ uwagê, ¿e `FINALIZED` przechodzi na done.

Co powiedzieæ:
- "Human-in-the-loop jest twardym wymaganiem: system nie finalizuje REVIEW bez decyzji cz³owieka."

## 4. DLQ + replay (60-90s)

1. Otwórz panel `DLQ Operations`.
2. Poka¿ event w DLQ (failed event type + attempt).
3. Kliknij `Replay`.
4. Poka¿ komunikat replay i odœwie¿enie stanu.

Co powiedzieæ:
- "Retry + DLQ + replay to œcie¿ka operacyjna, a nie ukryty demo trick."
- "Replay jest jawny i audytowalny przez event timeline."

## 5. Zamkniêcie (20s)

Podsumowanie dla rekrutera:
- event-driven orchestration przez Redis Streams,
- append-only audit trail w PostgreSQL,
- explainability i policy ruleset v2,
- human review dla REVIEW,
- operational maturity: retry/DLQ/replay + observability.
