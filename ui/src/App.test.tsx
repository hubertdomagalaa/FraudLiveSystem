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
  {
    case_id: 'case-2',
    transaction_id: 'tx-created',
    created_at: '2026-03-06T10:10:00Z',
    latest_decision: null,
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

    if (url.includes('/transactions') && init?.method === 'POST') {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            transaction_id: 'tx-created',
            received_at: '2026-03-06T10:10:00Z',
            amount: '1200.50',
            currency: 'USD',
            merchant_id: 'merchant-1',
            card_id: 'card-xyz',
            timestamp: '2026-03-06T10:10:00Z',
            country: 'US',
            ip: '198.51.100.10',
            device_id: 'dev-ui-001',
            prior_chargeback_flags: false,
            merchant_risk_score: 0.35,
            metadata: { new_device: true },
          }),
          { status: 201 },
        ),
      );
    }
    if (url.includes('/cases/case-1/events') || url.includes('/cases/case-2/events')) {
      return Promise.resolve(new Response(JSON.stringify(eventsResponse), { status: 200 }));
    }
    if (url.includes('/cases/case-1/agent-runs') || url.includes('/cases/case-2/agent-runs')) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes('/cases/case-1/decisions') || url.includes('/cases/case-2/decisions')) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes('/cases/case-1/reviews') || url.includes('/cases/case-2/reviews')) {
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
  expect(await screen.findByText('Why this decision?')).toBeInTheDocument();
  expect(await screen.findByText('Pipeline Status')).toBeInTheDocument();
  expect(await screen.findByText('INGESTED')).toBeInTheDocument();
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

test('creates transaction from intake form', async () => {
  render(<App />);

  const createButton = await screen.findByRole('button', { name: /create transaction/i });
  fireEvent.click(createButton);

  await waitFor(() => {
    expect(screen.getByText('Transaction created: tx-created')).toBeInTheDocument();
  });
});


test('applies demo preset in create transaction form', async () => {
  render(<App />);

  const lowRiskPreset = await screen.findByRole('button', { name: /low risk demo/i });
  fireEvent.click(lowRiskPreset);

  const amountInput = await screen.findByLabelText('Amount') as HTMLInputElement;
  expect(amountInput.value).toBe('180.00');
});


