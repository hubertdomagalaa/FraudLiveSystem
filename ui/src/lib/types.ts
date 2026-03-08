export type CaseSummary = {
  case_id: string;
  transaction_id: string;
  created_at: string;
  latest_decision?: string | null;
  decision_time?: string | null;
  latest_human_action?: string | null;
  human_action_time?: string | null;
};

export type CaseEvent = {
  event_id: string;
  event_type: string;
  producer_service: string;
  stream_name: string;
  occurred_at: string;
  recorded_at: string;
  trace_id?: string | null;
  traceparent?: string | null;
  payload: Record<string, unknown>;
};

export type AgentRun = {
  agent_run_id: string;
  agent_name: string;
  step_name: string;
  attempt: number;
  status: string;
  started_at: string;
  finished_at: string;
  latency_ms: number;
  agent_version?: string | null;
  error_code?: string | null;
  error_message?: string | null;
};

export type Decision = {
  decision_id: string;
  decision_kind: string;
  decision: string;
  confidence?: number | null;
  reason_summary?: string | null;
  reason_details: Record<string, unknown>;
  decided_by: string;
  source_event_id?: string | null;
  created_at: string;
};

export type ReviewAction = {
  review_action_id: string;
  reviewer_id?: string | null;
  action: string;
  reason_code?: string | null;
  notes?: string | null;
  source_event_id?: string | null;
  created_at: string;
};

export type DlqEvent = {
  event_id: string;
  case_id: string;
  transaction_id: string;
  stream_name: string;
  producer_service: string;
  occurred_at: string;
  trace_id?: string | null;
  traceparent?: string | null;
  payload: Record<string, unknown>;
};

export type ReviewDecisionInput = {
  reviewer_id: string;
  outcome: 'ALLOW' | 'BLOCK';
  comment: string;
  labels: string[];
};

export type ReplayResult = {
  replay_event_id: string;
  source_stream: string;
  stream_message_id: string;
  attempt: number;
};
