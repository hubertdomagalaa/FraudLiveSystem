import { useEffect, useState } from 'react';

import { api } from '../lib/api';
import { formatDate, prettyJson } from '../lib/format';
import type { DlqEvent } from '../lib/types';

type Props = {
  token: string;
};

function getFailedEventType(event: DlqEvent): string {
  const payload = event.payload as Record<string, unknown>;
  const failedEvent = payload.failed_event as Record<string, unknown> | undefined;
  return failedEvent && typeof failedEvent.event_type === 'string' ? failedEvent.event_type : 'unknown';
}

function getFailedAttempt(event: DlqEvent): number | null {
  const payload = event.payload as Record<string, unknown>;
  const failedEvent = payload.failed_event as Record<string, unknown> | undefined;
  return failedEvent && typeof failedEvent.attempt === 'number' ? failedEvent.attempt : null;
}

export function DlqPanel({ token }: Props) {
  const [events, setEvents] = useState<DlqEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function loadDlq() {
    setLoading(true);
    setStatus(null);
    try {
      setEvents(await api.listDlqEvents(token));
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Failed to load DLQ';
      setStatus(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDlq();
  }, [token]);

  async function replay(eventId: string) {
    if (!window.confirm(`Replay DLQ event ${eventId}?`)) {
      return;
    }

    try {
      const result = await api.replayDlqEvent(eventId, token);
      setStatus(`Replay submitted: ${result.replay_event_id} (attempt=${result.attempt})`);
      await loadDlq();
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Replay failed';
      setStatus(message);
    }
  }

  return (
    <section className="panel dlq-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Recovery Desk</p>
          <h2>DLQ Operations</h2>
        </div>
        <button className="ghost-button" onClick={() => void loadDlq()} type="button">
          Refresh DLQ
        </button>
      </div>

      {loading ? <p className="status-message">Loading DLQ events...</p> : null}
      {status ? <p className="status-message">{status}</p> : null}

      <div className="dlq-list">
        {events.map((event) => (
          <article className="dlq-card" key={event.event_id}>
            <div className="section-heading">
              <strong>{event.event_id}</strong>
              <button className="ghost-button" onClick={() => void replay(event.event_id)} type="button">
                Replay
              </button>
            </div>
            <small>
              Failed event: {getFailedEventType(event)} | attempt: {getFailedAttempt(event) ?? '-'}
            </small>
            <small>
              {event.case_id} | {formatDate(event.occurred_at)}
            </small>
            <pre>{prettyJson(event.payload)}</pre>
          </article>
        ))}
      </div>
    </section>
  );
}
