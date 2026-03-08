import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import App from './App';

const casesResponse = [
  {
    case_id: 'case-1',
    transaction_id: 'tx-1',
    created_at: '2026-03-06T10:00:00Z',
    latest_decision: 'REVIEW',
  },
];

const eventsResponse = [
  {
    event_id: 'event-1',
    event_type: 'case.created',
    producer_service: 'ingestion-api',
    stream_name: 'fraud.case.events.v1',
    occurred_at: '2026-03-06T10:00:00Z',
    recorded_at: '2026-03-06T10:00:00Z',
    trace_id: 'trace-1',
    traceparent: '00-1-1-01',
    payload: { hello: 'world' },
  },
];

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.includes('/cases/case-1/events')) {
      return Promise.resolve(new Response(JSON.stringify(eventsResponse), { status: 200 }));
    }
    if (url.includes('/cases/case-1/agent-runs')) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes('/cases/case-1/decisions')) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes('/cases/case-1/reviews')) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes('/dlq/events')) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.endsWith('/cases')) {
      return Promise.resolve(new Response(JSON.stringify(casesResponse), { status: 200 }));
    }
    if (url.includes('/decision') && init?.method === 'POST') {
      return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
  }) as typeof fetch);

  vi.stubGlobal('confirm', vi.fn(() => true));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test('renders case list and detail timeline', async () => {
  render(<App />);

  expect(await screen.findByText('Fraud Cases')).toBeInTheDocument();
  expect(await screen.findByText('case.created')).toBeInTheDocument();
});

test('submits manual review action', async () => {
  render(<App />);

  const submitButton = await screen.findByRole('button', { name: /submit review/i });
  fireEvent.click(submitButton);

  await waitFor(() => {
    expect(screen.getByText('Review decision submitted.')).toBeInTheDocument();
  });
});

