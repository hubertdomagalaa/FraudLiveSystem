import { formatDate } from '../lib/format';
import type { CaseSummary } from '../lib/types';

type Props = {
  cases: CaseSummary[];
  selectedCaseId: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (item: CaseSummary) => void;
  onRefresh: () => void;
};

export function CaseList({ cases, selectedCaseId, loading, error, onSelect, onRefresh }: Props) {
  return (
    <section className="panel case-list-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Operations Queue</p>
          <h2>Fraud Cases</h2>
        </div>
        <button className="ghost-button" onClick={onRefresh} type="button">
          Refresh
        </button>
      </div>

      {loading ? <p className="status-message">Loading cases...</p> : null}
      {error ? <p className="status-message error">{error}</p> : null}

      <div className="case-list">
        {cases.map((item) => (
          <button
            className={`case-row ${selectedCaseId === item.case_id ? 'selected' : ''}`}
            key={item.case_id}
            onClick={() => onSelect(item)}
            type="button"
          >
            <div>
              <strong>{item.latest_decision ?? 'OPEN'}</strong>
              <span>{item.transaction_id}</span>
            </div>
            <div>
              <small>{formatDate(item.created_at)}</small>
              <small>{item.case_id.slice(0, 8)}</small>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
