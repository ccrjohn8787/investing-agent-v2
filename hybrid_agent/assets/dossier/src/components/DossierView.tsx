import { useMemo, useState } from 'react';
import {
  AnalystDossier,
  GateRow,
  QAResult,
  ReverseDCFBlock,
  StageZeroTable,
  DeltaEntry,
  TriggerAlert,
} from '../types';
import { formatBand, formatCurrency, formatNumber, formatPercent } from '../utils/format';

interface Props {
  analyst: AnalystDossier;
  verifier?: QAResult;
  delta?: Record<string, DeltaEntry> | null;
  triggers?: TriggerAlert[];
  triggerAlerts?: TriggerAlert[];
}

const normalizeStageZero = (stage0?: StageZeroTable | GateRow[]): { hard: GateRow[]; soft: GateRow[] } => {
  if (!stage0) {
    return { hard: [], soft: [] };
  }
  if (Array.isArray(stage0)) {
    return { hard: stage0 ?? [], soft: [] };
  }
  return {
    hard: stage0.hard ?? [],
    soft: stage0.soft ?? [],
  };
};

const defaultScenarioNames = ['Bear', 'Base', 'Bull'];

const DossierView = ({ analyst, verifier, delta, triggers, triggerAlerts }: Props) => {
  const stage0 = useMemo(() => normalizeStageZero(analyst.stage_0), [analyst.stage_0]);
  const [showProvenance, setShowProvenance] = useState(false);
  const provenance = analyst.provenance ?? analyst.metrics ?? [];
  const reverse = analyst.reverse_dcf;
  const qaStatus = verifier?.status ?? 'PENDING';
  const deltaData = delta ?? analyst.delta ?? {};
  const triggerList = triggers ?? analyst.triggers ?? [];
  const triggerAlertsList = triggerAlerts ?? analyst.trigger_alerts ?? [];

  return (
    <div className="dossier">
      <div className="section-card">
        <div className="grid-two">
          <div>
            <h2>Analyst Verdict</h2>
            <p className="stage1-text">{analyst.output_0}</p>
            {analyst.path_reasons && analyst.path_reasons.length > 0 && (
              <div className="tags">
                {analyst.path_reasons.map((reason) => (
                  <span key={reason} className="tag">
                    {reason}
                  </span>
                ))}
              </div>
            )}
            {analyst.provenance_issues && analyst.provenance_issues.length > 0 && (
              <div className="status-warning" style={{ marginTop: '1rem' }}>
                <strong>Provenance Alerts:</strong>
                <ul className="qa-reasons">
                  {analyst.provenance_issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div>
            <h2>QA Status</h2>
            <span className={`badge ${qaStatus === 'PASS' ? 'badge-pass' : qaStatus === 'BLOCKER' ? 'badge-blocker' : ''}`}>
              {qaStatus === 'PASS' && 'QA PASS'}
              {qaStatus === 'BLOCKER' && 'QA BLOCKER'}
              {qaStatus === 'PENDING' && 'QA PENDING'}
            </span>
            {verifier?.reasons && verifier.reasons.length > 0 && (
              <ul className="qa-reasons">
                {verifier.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {triggerAlertsList && triggerAlertsList.length > 0 && (
              <div className="status-warning" style={{ marginTop: '1rem' }}>
                <strong>Trigger Alerts</strong>
                <ul className="qa-reasons">
                  {triggerAlertsList.map((alert, index) => (
                    <li key={`${alert.trigger ?? 'alert'}-${index}`}>
                      {alert.trigger ? `${alert.trigger}: ` : ''}
                      {alert.message}
                      {typeof alert.days_remaining === 'number' && (
                        <span className="muted"> (days remaining: {alert.days_remaining})</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid-two" style={{ marginTop: '1.5rem' }}>
        <StageZeroSection label="Hard Gates" rows={stage0.hard} />
        <StageZeroSection label="Soft Gates" rows={stage0.soft} />
      </div>

      <div className="section-card" style={{ marginTop: '1.5rem' }}>
        <h2>Stage-1 Narrative</h2>
        <div className="stage1-text">{analyst.stage_1 ?? 'NA'}</div>
      </div>

      <ReverseDcfSection block={reverse} />

      <DeltaSection delta={deltaData} />

      <TriggersSection triggers={triggerList} />

      <FinalGateSection finalGate={analyst.final_gate} />

      <EvidenceSection evidence={analyst.evidence} />

      <div className="section-card" style={{ marginTop: '1.5rem' }}>
        <h2>Provenance</h2>
        <button className="toggle" type="button" onClick={() => setShowProvenance((prev) => !prev)}>
          {showProvenance ? 'Hide details' : 'Show details'}
        </button>
        {showProvenance && provenance.length > 0 ? (
          <table className="table" style={{ marginTop: '1rem' }}>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Period</th>
                <th>Document</th>
                <th>Page/Section</th>
                <th>Quote</th>
              </tr>
            </thead>
            <tbody>
              {provenance.map((entry, index) => (
                <tr key={`${entry.metric ?? 'metric'}-${index}`}>
                  <td>{entry.metric}</td>
                  <td>{formatNumber(entry.value ?? 'NA')}</td>
                  <td>{entry.period ?? 'NA'}</td>
                  <td>
                    {entry.url ? (
                      <a href={entry.url} target="_blank" rel="noreferrer">
                        {entry.source_doc_id ?? 'source'}
                      </a>
                    ) : (
                      entry.source_doc_id ?? 'NA'
                    )}
                  </td>
                  <td>{entry.page_or_section ?? 'NA'}</td>
                  <td>{entry.quote ?? 'NA'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          showProvenance && <div className="muted">No provenance entries available.</div>
        )}
      </div>
    </div>
  );
};

const StageZeroSection = ({ label, rows }: { label: string; rows: GateRow[] }) => (
  <div className="section-card">
    <h2>{label}</h2>
    {rows.length === 0 ? (
      <div className="muted">NA</div>
    ) : (
      <table className="table">
        <thead>
          <tr>
            <th>Gate</th>
            <th>What it means</th>
            <th>Pass rule</th>
            <th>Result</th>
            <th>Metrics &amp; Sources</th>
            <th>Flip-trigger</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${label}-${row.gate}`}>
              <td>{row.gate}</td>
              <td>{row.what_it_means ?? '—'}</td>
              <td>{row.pass_rule ?? '—'}</td>
              <td>{row.result}</td>
              <td>
                {row.metrics_sources && row.metrics_sources.length > 0
                  ? row.metrics_sources.map((source) => <div key={source}>{source}</div>)
                  : '—'}
              </td>
              <td>{row.flip_trigger ?? '—'}</td>
              <td>
                {row.evidence && row.evidence.length > 0
                  ? row.evidence.map((item, idx) => <div key={`${row.gate}-evidence-${idx}`}>{item}</div>)
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

const ReverseDcfSection = ({ block }: { block?: ReverseDCFBlock }) => {
  if (!block) {
    return (
      <div className="section-card" style={{ marginTop: '1.5rem' }}>
        <h2>Reverse DCF</h2>
        <div className="muted">NA</div>
      </div>
    );
  }

  const scenarios = block.scenarios && block.scenarios.length > 0 ? block.scenarios : defaultScenarioNames.map((name) => ({ name, fcf_path: [], irr: null }));
  const keys = block.sensitivity ? Object.keys(block.sensitivity) : [];

  return (
    <div className="section-card" style={{ marginTop: '1.5rem' }}>
      <h2>Reverse DCF &amp; IRR</h2>
      <div className="grid-two">
        <div>
          <dl className="key-value">
            <dt>WACC</dt>
            <dd>
              {block.wacc?.point !== undefined && block.wacc?.point !== null
                ? `${formatPercent(block.wacc.point)} (${formatBand(block.wacc.band ?? null)})`
                : 'NA'}
            </dd>
            <dt>Terminal g</dt>
            <dd>{formatPercent(block.terminal_growth?.value ?? null)}</dd>
            <dt>Hurdle IRR</dt>
            <dd>{formatPercent(block.hurdle?.value ?? null)}</dd>
            <dt>Cost of Equity</dt>
            <dd>{formatPercent(block.wacc?.cost_of_equity ?? null)}</dd>
            <dt>Cost of Debt (after tax)</dt>
            <dd>{formatPercent(block.wacc?.cost_of_debt_after_tax ?? null)}</dd>
            <dt>TTM FCF</dt>
            <dd>{formatCurrency(block.ttm_fcf ?? null)}</dd>
            <dt>Price</dt>
            <dd>{formatCurrency(block.price ?? null)}</dd>
            <dt>Shares</dt>
            <dd>{block.shares ? `${(block.shares / 1_000_000_000).toFixed(2)}B` : 'NA'}</dd>
          </dl>
          {block.notes && <p className="muted">{block.notes}</p>}
        </div>
        <div>
          <h3>Sensitivity</h3>
          {keys.length === 0 ? (
            <div className="muted">NA</div>
          ) : (
            <ul className="list-unstyled">
              {keys.map((key) => (
                <li key={key}>
                  <strong>{key}:</strong> {formatPercent(block.sensitivity?.[key] ?? null)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="scenario-grid">
        {scenarios.map((scenario) => (
          <div key={scenario.name} className="scenario-card">
            <h4>{scenario.name}</h4>
            <div className="muted">IRR: {formatPercent(scenario.irr ?? null)}</div>
            {scenario.fcf_path && scenario.fcf_path.length > 0 ? (
              <div className="muted" style={{ marginTop: '0.5rem' }}>
                {scenario.fcf_path.map((value, idx) => (
                  <span key={idx}>{idx > 0 ? ', ' : ''}{formatCurrency(value)}</span>
                ))}
              </div>
            ) : (
              <div className="muted" style={{ marginTop: '0.5rem' }}>No FCF path provided.</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const FinalGateSection = ({ finalGate }: { finalGate?: Record<string, { definition?: string; evidence?: string; pass_fail?: string }> }) => (
  <div className="section-card" style={{ marginTop: '1.5rem' }}>
    <h2>Final Decision Gate</h2>
    {finalGate ? (
      <div className="grid-two">
        {Object.entries(finalGate).map(([key, value]) => (
          <div key={key} className="scenario-card">
            <h4>{key.replace(/_/g, ' ')}</h4>
            <p>{value.definition ?? 'Definition pending.'}</p>
            {value.evidence && <p className="muted">Evidence: {value.evidence}</p>}
            {value.pass_fail && <p><strong>Outcome:</strong> {value.pass_fail}</p>}
          </div>
        ))}
      </div>
    ) : (
      <div className="muted">NA</div>
    )}
  </div>
);

const EvidenceSection = ({ evidence }: { evidence?: AnalystDossier['evidence'] }) => (
  <div className="section-card" style={{ marginTop: '1.5rem' }}>
    <h2>Evidence Highlights</h2>
    {evidence && evidence.length > 0 ? (
      <ul className="list-unstyled">
        {evidence.map((item, idx) => (
          <li key={`${item.intent}-${idx}`}>
            <strong>{item.intent ?? 'Evidence'}:</strong> {item.excerpt ?? 'Excerpt unavailable.'}
          </li>
        ))}
      </ul>
    ) : (
      <div className="muted">Evidence not attached.</div>
    )}
  </div>
);

const DeltaSection = ({ delta }: { delta: Record<string, DeltaEntry> }) => (
  <div className="section-card" style={{ marginTop: '1.5rem' }}>
    <h2>Delta Highlights</h2>
    {delta && Object.keys(delta).length > 0 ? (
      <table className="table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Current</th>
            <th>QoQ</th>
            <th>QoQ %</th>
            <th>YoY</th>
            <th>YoY %</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(delta).map(([metric, values]) => (
            <tr key={metric}>
              <td>{metric}</td>
              <td>{formatCurrency(values.current)}</td>
              <td>{formatCurrency(values.qoq)}</td>
              <td>{formatPercent(values.qoq_percent)}</td>
              <td>{formatCurrency(values.yoy)}</td>
              <td>{formatPercent(values.yoy_percent)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    ) : (
      <div className="muted">NA</div>
    )}
  </div>
);

const TriggersSection = ({ triggers }: { triggers: TriggerAlert[] }) => (
  <div className="section-card" style={{ marginTop: '1.5rem' }}>
    <h2>Trigger Monitor</h2>
    {triggers && triggers.length > 0 ? (
      <table className="table">
        <thead>
          <tr>
            <th>Trigger</th>
            <th>Threshold</th>
            <th>Comparison</th>
            <th>Deadline</th>
          </tr>
        </thead>
        <tbody>
          {triggers.map((trigger, idx) => (
            <tr key={`${trigger.trigger ?? trigger.message}-${idx}`}>
              <td>{trigger.trigger ?? 'NA'}</td>
              <td>{trigger.threshold !== undefined ? formatNumber(trigger.threshold) : 'NA'}</td>
              <td>{trigger.comparison ?? trigger.status ?? 'NA'}</td>
              <td>{trigger.deadline ?? 'NA'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    ) : (
      <div className="muted">No active triggers.</div>
    )}
  </div>
);

export default DossierView;
