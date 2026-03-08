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

const emptyState: DetailsState = {
  events: [],
  agentRuns: [],
  decisions: [],
  reviews: [],
};

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
