import { useEffect, useState } from 'react';

import { CaseDetails } from './components/CaseDetails';
import { CaseList } from './components/CaseList';
import { DlqPanel } from './components/DlqPanel';
import { ReviewPanel } from './components/ReviewPanel';
import { api } from './lib/api';
import type { CaseSummary } from './lib/types';

export default function App() {
  const [token, setToken] = useState('');
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  async function loadCases() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.listCases(token);
      setCases(result);
      setSelectedCase((current) => result.find((item) => item.case_id === current?.case_id) ?? result[0] ?? null);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Failed to load cases';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadCases();
  }, [token, refreshKey]);

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Fraud Decision Support</p>
          <h1>Caseflow Control Console</h1>
          <p className="hero-copy">
            Review live fraud cases, inspect append-only evidence, submit human decisions and recover DLQ traffic from one console.
          </p>
        </div>
        <div className="hero-panel">
          <label>
            Bearer Token
            <input
              onChange={(event) => setToken(event.target.value)}
              placeholder="Paste JWT with fraud.write scope"
              value={token}
            />
          </label>
          <button className="solid-button" onClick={() => setRefreshKey((value) => value + 1)} type="button">
            Reload workspace
          </button>
        </div>
      </header>

      <main className="workspace-grid">
        <CaseList
          cases={cases}
          error={error}
          loading={loading}
          onRefresh={() => setRefreshKey((value) => value + 1)}
          onSelect={setSelectedCase}
          selectedCaseId={selectedCase?.case_id ?? null}
        />
        <CaseDetails refreshKey={refreshKey} selectedCase={selectedCase} token={token} />
        <div className="side-stack">
          <ReviewPanel
            onSubmitted={() => {
              setRefreshKey((value) => value + 1);
            }}
            selectedCase={selectedCase}
            token={token}
          />
          <DlqPanel token={token} />
        </div>
      </main>
    </div>
  );
}
