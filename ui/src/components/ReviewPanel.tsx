import { useState } from 'react';

import { api } from '../lib/api';
import type { CaseSummary } from '../lib/types';

type Props = {
  selectedCase: CaseSummary | null;
  token: string;
  onSubmitted: () => void;
};

export function ReviewPanel({ selectedCase, token, onSubmitted }: Props) {
  const [reviewerId, setReviewerId] = useState('reviewer-1');
  const [outcome, setOutcome] = useState<'ALLOW' | 'BLOCK'>('ALLOW');
  const [comment, setComment] = useState('verified');
  const [labels, setLabels] = useState('manual_ok');
  const [status, setStatus] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submitReview() {
    if (!selectedCase) {
      return;
    }

    setPending(true);
    setStatus(null);
    try {
      await api.submitReviewDecision(selectedCase.case_id, token, {
        reviewer_id: reviewerId,
        outcome,
        comment,
        labels: labels.split(',').map((item) => item.trim()).filter(Boolean),
      });
      setStatus('Review decision submitted.');
      onSubmitted();
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Failed to submit review decision';
      setStatus(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="panel review-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Human in the Loop</p>
          <h2>Manual Review</h2>
        </div>
      </div>

      {!selectedCase ? <p className="muted">Select a case before sending a manual decision.</p> : null}

      <label>
        Reviewer ID
        <input value={reviewerId} onChange={(event) => setReviewerId(event.target.value)} />
      </label>
      <label>
        Outcome
        <select value={outcome} onChange={(event) => setOutcome(event.target.value as 'ALLOW' | 'BLOCK')}>
          <option value="ALLOW">ALLOW</option>
          <option value="BLOCK">BLOCK</option>
        </select>
      </label>
      <label>
        Comment
        <textarea rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
      </label>
      <label>
        Labels
        <input value={labels} onChange={(event) => setLabels(event.target.value)} />
      </label>

      <button className="solid-button" disabled={!selectedCase || pending} onClick={submitReview} type="button">
        {pending ? 'Submitting...' : 'Submit review'}
      </button>

      {status ? <p className="status-message">{status}</p> : null}
    </section>
  );
}
