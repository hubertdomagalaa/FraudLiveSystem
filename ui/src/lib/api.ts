import type {
  AgentRun,
  CaseEvent,
  CaseSummary,
  Decision,
  DlqEvent,
  ReplayResult,
  ReviewAction,
  ReviewDecisionInput,
  TransactionCreateInput,
  TransactionStored,
} from './types';

const orchestratorBaseUrl = import.meta.env.VITE_ORCHESTRATOR_API_URL ?? 'http://localhost:8002/v1';
const humanReviewBaseUrl = import.meta.env.VITE_HUMAN_REVIEW_API_URL ?? 'http://localhost:8003/v1';
const dlqBaseUrl = import.meta.env.VITE_DLQ_API_URL ?? 'http://localhost:8004/v1';
const ingestionBaseUrl = import.meta.env.VITE_INGESTION_API_URL ?? 'http://localhost:8001/v1';

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function authHeaders(token: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const api = {
  listCases: (token: string) =>
    requestJson<CaseSummary[]>(`${orchestratorBaseUrl}/cases`, { headers: authHeaders(token) }),
  getCaseEvents: (caseId: string, token: string) =>
    requestJson<CaseEvent[]>(`${orchestratorBaseUrl}/cases/${caseId}/events`, { headers: authHeaders(token) }),
  getAgentRuns: (caseId: string, token: string) =>
    requestJson<AgentRun[]>(`${orchestratorBaseUrl}/cases/${caseId}/agent-runs`, { headers: authHeaders(token) }),
  getDecisions: (caseId: string, token: string) =>
    requestJson<Decision[]>(`${orchestratorBaseUrl}/cases/${caseId}/decisions`, { headers: authHeaders(token) }),
  getReviews: (caseId: string, token: string) =>
    requestJson<ReviewAction[]>(`${orchestratorBaseUrl}/cases/${caseId}/reviews`, { headers: authHeaders(token) }),
  createTransaction: (token: string, payload: TransactionCreateInput, idempotencyKey: string) =>
    requestJson<TransactionStored>(`${ingestionBaseUrl}/transactions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
        ...authHeaders(token),
      },
      body: JSON.stringify(payload),
    }),
  submitReviewDecision: (caseId: string, token: string, payload: ReviewDecisionInput) =>
    requestJson(`${humanReviewBaseUrl}/cases/${caseId}/decision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(token),
      },
      body: JSON.stringify(payload),
    }),
  listDlqEvents: (token: string) =>
    requestJson<DlqEvent[]>(`${dlqBaseUrl}/dlq/events`, { headers: authHeaders(token) }),
  replayDlqEvent: (eventId: string, token: string) =>
    requestJson<ReplayResult>(`${dlqBaseUrl}/dlq/replay/${eventId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(token),
      },
      body: JSON.stringify({ reset_attempt: true }),
    }),
};
