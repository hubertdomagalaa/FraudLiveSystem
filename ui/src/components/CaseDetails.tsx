import { useEffect, useState } from 'react';

import { api } from '../lib/api';
import { formatDate, prettyJson } from '../lib/format';
import type { AgentRun, CaseEvent, CaseSummary, Decision, ReviewAction } from '../lib/types';

type Props = {
  selectedCase: CaseSummary | null;
  token: string;
  refreshKey: number;
};

type DetailsState = {
  events: CaseEvent[];
  agentRuns: AgentRun[];
  decisions: Decision[];
  reviews: ReviewAction[];
};

type DecisionWhy = {
  recommendation: string;
  riskScore: number | null;
  signals: string[];
  policyViolations: string[];
  explanation: string;
};

type PipelineStep = {
  name: string;
  done: boolean;
};

const emptyState: DetailsState = {
  events: [],
  agentRuns: [],
  decisions: [],
  reviews: [],
};

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object') {
    return value as Record<string, unknown>;
  }
  return {};
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item));
}

function latestEvent(events: CaseEvent[], eventType: string): CaseEvent | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    if (events[index].event_type === eventType) {
      return events[index];
    }
  }
  return null;
}

function derivePipelineStatuses(events: CaseEvent[], decisions: Decision[], reviews: ReviewAction[]): PipelineStep[] {
  const eventTypes = new Set(events.map((event) => event.event_type));
  const hasFinalDecision = decisions.some((decision) => decision.decision_kind === 'FINAL');
  const hasReviewRequired =
    eventTypes.has('case.human_review.required') || reviews.some((review) => review.action === 'REVIEW_REQUESTED');

  return [
    { name: 'INGESTED', done: eventTypes.has('case.created') },
    { name: 'CONTEXT_DONE', done: eventTypes.has('agent.context.completed') },
    { name: 'RISK_DONE', done: eventTypes.has('agent.risk.completed') },
    { name: 'POLICY_DONE', done: eventTypes.has('agent.policy.completed') },
    { name: 'EXPLAIN_DONE', done: eventTypes.has('agent.explain.completed') },
    { name: 'AGGREGATED', done: eventTypes.has('agent.aggregate.completed') },
    { name: 'REVIEW_REQUIRED', done: hasReviewRequired },
    { name: 'FINALIZED', done: eventTypes.has('case.finalized') || hasFinalDecision },
  ];
}

function deriveDecisionWhy(events: CaseEvent[], selectedCase: CaseSummary): DecisionWhy {
  const contextPayload = asRecord(asRecord(latestEvent(events, 'agent.context.completed')?.payload).result);
  const riskPayload = asRecord(asRecord(latestEvent(events, 'agent.risk.completed')?.payload).result);
  const policyPayload = asRecord(asRecord(latestEvent(events, 'agent.policy.completed')?.payload).result);
  const aggregatePayload = asRecord(latestEvent(events, 'agent.aggregate.completed')?.payload);
  const explainPayload = asRecord(asRecord(latestEvent(events, 'agent.explain.completed')?.payload).result);

  const recommendation = String(
    aggregatePayload.recommendation ?? policyPayload.action ?? selectedCase.latest_decision ?? 'OPEN',
  );

  const riskScoreValue = aggregatePayload.risk_score ?? riskPayload.risk_score;
  const riskScore = typeof riskScoreValue === 'number' ? riskScoreValue : null;

  const aggregateSignals = asStringArray(aggregatePayload.signals);
  const contextSignals = asStringArray(contextPayload.signals);
  const riskSignals = asStringArray(riskPayload.risk_signals);
  const signals = [...new Set([...aggregateSignals, ...contextSignals, ...riskSignals])];

  const policyViolations = asStringArray(aggregatePayload.policy_violations);
  const fallbackPolicyViolations = asStringArray(policyPayload.violations);

  const explanation = String(
    aggregatePayload.explanation ??
      explainPayload.summary ??
      policyPayload.explanation ??
      riskPayload.explanation ??
      'No explanation available yet.',
  );

  return {
    recommendation,
    riskScore,
    signals,
    policyViolations: policyViolations.length > 0 ? policyViolations : fallbackPolicyViolations,
    explanation,
  };
}

export function CaseDetails({ selectedCase, token, refreshKey }: Props) {
  const [state, setState] = useState<DetailsState>(emptyState);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedCase) {
      setState(emptyState);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.getCaseEvents(selectedCase.case_id, token),
      api.getAgentRuns(selectedCase.case_id, token),
      api.getDecisions(selectedCase.case_id, token),
      api.getReviews(selectedCase.case_id, token),
    ])
      .then(([events, agentRuns, decisions, reviews]) => {
        if (cancelled) {
          return;
        }
        setState({ events, agentRuns, decisions, reviews });
      })
      .catch((cause: Error) => {
        if (!cancelled) {
          setError(cause.message || 'Failed to load case details');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey, selectedCase, token]);

  if (!selectedCase) {
    return <section className="panel details-empty">Select a case to inspect its timeline and actions.</section>;
  }

  const why = deriveDecisionWhy(state.events, selectedCase);
  const pipeline = derivePipelineStatuses(state.events, state.decisions, state.reviews);

  return (
    <section className="panel details-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Case Control Room</p>
          <h2>{selectedCase.case_id}</h2>
        </div>
        <div className="detail-badges">
          <span className="badge badge-hot">{selectedCase.latest_decision ?? 'OPEN'}</span>
          <span className="badge">{selectedCase.transaction_id}</span>
        </div>
      </div>

      {loading ? <p className="status-message">Loading case details...</p> : null}
      {error ? <p className="status-message error">{error}</p> : null}

      <article className="detail-card">
        <h3>Pipeline Status</h3>
        <div className="status-grid">
          {pipeline.map((step) => (
            <span className={`status-pill ${step.done ? 'done' : 'pending'}`} key={step.name}>
              {step.name}
            </span>
          ))}
        </div>
      </article>

      <article className="detail-card why-card">
        <div className="section-heading">
          <h3>Why this decision?</h3>
          <span className="badge badge-hot">{why.recommendation}</span>
        </div>
        <div className="why-grid">
          <div>
            <small>Risk Score</small>
            <p className="why-value">{why.riskScore !== null ? why.riskScore.toFixed(2) : '-'}</p>
          </div>
          <div>
            <small>Policy Violations</small>
            <p className="why-value">{why.policyViolations.length > 0 ? why.policyViolations.join(', ') : 'None'}</p>
          </div>
        </div>
        <div>
          <small>Signals</small>
          <p className="why-value">{why.signals.length > 0 ? why.signals.join(', ') : 'No explicit signals yet.'}</p>
        </div>
        <div>
          <small>Explanation</small>
          <p className="muted">{why.explanation}</p>
        </div>
      </article>

      <div className="detail-grid">
        <article className="detail-card">
          <h3>Decisions</h3>
          {state.decisions.map((decision) => (
            <div key={decision.decision_id} className="timeline-item compact">
              <strong>{decision.decision_kind}</strong>
              <span>{decision.decision}</span>
              <small>{formatDate(decision.created_at)}</small>
            </div>
          ))}
        </article>

        <article className="detail-card">
          <h3>Agent Runs</h3>
          {state.agentRuns.map((run) => (
            <div key={run.agent_run_id} className="timeline-item compact">
              <strong>{run.step_name}</strong>
              <span>{run.status}</span>
              <small>{run.latency_ms} ms</small>
            </div>
          ))}
        </article>
      </div>

      <article className="detail-card timeline-card">
        <div className="section-heading">
          <h3>Event Timeline</h3>
          <span className="trace-pill">{state.events[0]?.trace_id ?? 'no-trace'}</span>
        </div>
        <div className="timeline-list">
          {state.events.map((event) => (
            <div key={event.event_id} className="timeline-item">
              <div className="timeline-topline">
                <strong>{event.event_type}</strong>
                <span>{event.producer_service}</span>
              </div>
              <small>
                {formatDate(event.occurred_at)} | {event.stream_name}
              </small>
              <pre>{prettyJson(event.payload)}</pre>
            </div>
          ))}
        </div>
      </article>

      <article className="detail-card">
        <h3>Review Actions</h3>
        {state.reviews.length === 0 ? <p className="muted">No review actions yet.</p> : null}
        {state.reviews.map((review) => (
          <div key={review.review_action_id} className="timeline-item compact">
            <strong>{review.action}</strong>
            <span>{review.reviewer_id ?? 'queue'}</span>
            <small>{formatDate(review.created_at)}</small>
          </div>
        ))}
      </article>
    </section>
  );
}
