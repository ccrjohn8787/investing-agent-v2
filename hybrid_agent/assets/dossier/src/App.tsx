import { FormEvent, useEffect, useState } from 'react';
import DossierView from './components/DossierView';
import { AppProps, ReportPayload } from './types';

async function fetchReport(ticker: string): Promise<ReportPayload | null> {
  try {
    const response = await fetch(`/reports/${ticker}`);
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as ReportPayload;
  } catch (error) {
    console.warn('Failed to fetch dossier', error);
    return null;
  }
}

const App = ({ initialPayload, initialTicker = 'UBER' }: AppProps) => {
  const [ticker, setTicker] = useState(initialTicker.toUpperCase());
  const [payload, setPayload] = useState<ReportPayload | null>(initialPayload ?? null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!initialPayload) {
      loadTicker(initialTicker);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTicker = async (symbol: string) => {
    setLoading(true);
    const next = await fetchReport(symbol);
    if (!next) {
      setMessage(`Unable to load dossier for ${symbol}.`);
      setPayload(null);
    } else {
      setMessage(null);
      setPayload(next);
    }
    setLoading(false);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    loadTicker(ticker);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Hybrid Investment Dossier</h1>
        <form className="ticker-form" onSubmit={handleSubmit}>
          <label htmlFor="ticker">Ticker</label>
          <input
            id="ticker"
            name="ticker"
            value={ticker}
            onChange={(event) => setTicker(event.target.value.toUpperCase())}
            placeholder="UBER"
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Loading…' : 'Load'}
          </button>
        </form>
      </header>
      {message && <div className="status status-warning">{message}</div>}
      {payload ? (
        <DossierView
          analyst={payload.analyst}
          verifier={payload.verifier}
          delta={payload.delta ?? payload.analyst.delta}
          triggers={payload.triggers ?? payload.analyst.triggers ?? []}
          triggerAlerts={payload.trigger_alerts ?? payload.analyst.trigger_alerts ?? []}
        />
      ) : (
        !loading && <div className="status">Select a ticker to view the dossier.</div>
      )}
    </div>
  );
};

export default App;
