import { useState } from 'react';

import { api } from '../lib/api';
import type { TransactionCreateInput } from '../lib/types';

type Props = {
  token: string;
  onCreated: (transactionId: string) => void;
};

type FormState = {
  amount: string;
  currency: string;
  merchant_id: string;
  card_id: string;
  timestamp: string;
  country: string;
  ip: string;
  device_id: string;
  prior_chargeback_flags: boolean;
  merchant_risk_score: string;
  metadataJson: string;
};

type Preset = {
  id: 'low-risk' | 'high-risk' | 'needs-review';
  label: string;
  values: FormState;
};

function nowIsoForInput(): string {
  const date = new Date();
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function buildIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `ui-${crypto.randomUUID()}`;
  }
  return `ui-${Date.now()}`;
}

const initialState: FormState = {
  amount: '1200.50',
  currency: 'USD',
  merchant_id: 'merchant-1',
  card_id: 'card-xyz',
  timestamp: nowIsoForInput(),
  country: 'US',
  ip: '198.51.100.10',
  device_id: 'dev-ui-001',
  prior_chargeback_flags: false,
  merchant_risk_score: '0.35',
  metadataJson: '{"device_trust":"unverified","new_device":true}',
};

function withFreshTimestamp(values: Omit<FormState, 'timestamp'>): FormState {
  return { ...values, timestamp: nowIsoForInput() };
}

const presets: Preset[] = [
  {
    id: 'low-risk',
    label: 'Low Risk Demo',
    values: withFreshTimestamp({
      amount: '180.00',
      currency: 'USD',
      merchant_id: 'merchant-low-risk',
      card_id: 'card-low-risk',
      country: 'US',
      ip: '198.51.100.20',
      device_id: 'dev-known-001',
      prior_chargeback_flags: false,
      merchant_risk_score: '0.12',
      metadataJson: '{"device_trust":"trusted","account_age_days":500,"new_device":false}',
    }),
  },
  {
    id: 'high-risk',
    label: 'High Risk Demo',
    values: withFreshTimestamp({
      amount: '22000.00',
      currency: 'USD',
      merchant_id: 'merchant-high-risk',
      card_id: 'card-high-risk',
      country: 'NG',
      ip: '203.0.113.80',
      device_id: 'dev-new-911',
      prior_chargeback_flags: true,
      merchant_risk_score: '0.95',
      metadataJson: '{"device_trust":"unverified","new_device":true,"high_velocity":true,"account_age_days":1}',
    }),
  },
  {
    id: 'needs-review',
    label: 'Needs Review Demo',
    values: withFreshTimestamp({
      amount: '4200.00',
      currency: 'USD',
      merchant_id: 'merchant-review',
      card_id: 'card-review',
      country: 'ID',
      ip: '203.0.113.55',
      device_id: 'dev-review-007',
      prior_chargeback_flags: false,
      merchant_risk_score: '0.62',
      metadataJson: '{"device_trust":"unverified","new_device":true,"account_age_days":5}',
    }),
  },
];

export function CreateTransactionForm({ token, onCreated }: Props) {
  const [form, setForm] = useState<FormState>(initialState);
  const [status, setStatus] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function applyPreset(preset: Preset) {
    setForm(preset.values);
    setStatus(`Preset loaded: ${preset.label}`);
  }

  async function submitTransaction() {
    setPending(true);
    setStatus(null);

    try {
      const parsedMetadata = JSON.parse(form.metadataJson || '{}') as Record<string, unknown>;
      const payload: TransactionCreateInput = {
        amount: Number(form.amount),
        currency: form.currency.trim().toUpperCase(),
        merchant_id: form.merchant_id.trim(),
        card_id: form.card_id.trim(),
        timestamp: new Date(form.timestamp).toISOString(),
        metadata: parsedMetadata,
      };

      if (form.country.trim()) {
        payload.country = form.country.trim().toUpperCase();
      }
      if (form.ip.trim()) {
        payload.ip = form.ip.trim();
      }
      if (form.device_id.trim()) {
        payload.device_id = form.device_id.trim();
      }
      payload.prior_chargeback_flags = form.prior_chargeback_flags;
      if (form.merchant_risk_score.trim()) {
        payload.merchant_risk_score = Number(form.merchant_risk_score);
      }

      const transaction = await api.createTransaction(token, payload, buildIdempotencyKey());
      setStatus(`Transaction created: ${transaction.transaction_id}`);
      onCreated(transaction.transaction_id);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Failed to create transaction';
      setStatus(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="panel create-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Case Intake</p>
          <h2>Create Transaction</h2>
        </div>
      </div>

      <div className="preset-row">
        {presets.map((preset) => (
          <button className="ghost-button" key={preset.id} onClick={() => applyPreset(preset)} type="button">
            {preset.label}
          </button>
        ))}
      </div>

      <div className="form-grid two-columns">
        <label>
          Amount
          <input onChange={(event) => updateField('amount', event.target.value)} type="number" value={form.amount} />
        </label>
        <label>
          Currency
          <input maxLength={3} onChange={(event) => updateField('currency', event.target.value)} value={form.currency} />
        </label>
        <label>
          Merchant ID
          <input onChange={(event) => updateField('merchant_id', event.target.value)} value={form.merchant_id} />
        </label>
        <label>
          Card ID
          <input onChange={(event) => updateField('card_id', event.target.value)} value={form.card_id} />
        </label>
        <label>
          Timestamp
          <input onChange={(event) => updateField('timestamp', event.target.value)} type="datetime-local" value={form.timestamp} />
        </label>
        <label>
          Country
          <input maxLength={2} onChange={(event) => updateField('country', event.target.value)} value={form.country} />
        </label>
        <label>
          IP
          <input onChange={(event) => updateField('ip', event.target.value)} value={form.ip} />
        </label>
        <label>
          Device ID
          <input onChange={(event) => updateField('device_id', event.target.value)} value={form.device_id} />
        </label>
        <label>
          Merchant Risk Score (0-1)
          <input
            max="1"
            min="0"
            onChange={(event) => updateField('merchant_risk_score', event.target.value)}
            step="0.01"
            type="number"
            value={form.merchant_risk_score}
          />
        </label>
        <label className="checkbox-row">
          <input
            checked={form.prior_chargeback_flags}
            onChange={(event) => updateField('prior_chargeback_flags', event.target.checked)}
            type="checkbox"
          />
          Prior chargeback flags
        </label>
      </div>

      <label>
        Metadata (JSON)
        <textarea
          onChange={(event) => updateField('metadataJson', event.target.value)}
          rows={3}
          value={form.metadataJson}
        />
      </label>

      <button className="solid-button" disabled={pending} onClick={() => void submitTransaction()} type="button">
        {pending ? 'Creating...' : 'Create transaction'}
      </button>

      {status ? <p className="status-message">{status}</p> : null}
    </section>
  );
}
