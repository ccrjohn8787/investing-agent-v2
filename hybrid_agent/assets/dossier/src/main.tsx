import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './App.css';
import { ReportPayload } from './types';

declare global {
  interface Window {
    __DOSSIER__?: ReportPayload;
    __DOSSIER_TICKER__?: string;
  }
}

const container = document.getElementById('root');
if (container) {
  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <App initialPayload={window.__DOSSIER__} initialTicker={window.__DOSSIER_TICKER__ || 'UBER'} />
    </React.StrictMode>
  );
}
