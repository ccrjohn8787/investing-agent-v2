export interface GateRow {
  gate: string;
  result: string;
  what_it_means?: string;
  metrics_sources?: string[];
  pass_rule?: string;
  flip_trigger?: string | null;
  hard_or_soft?: 'Hard' | 'Soft';
  evidence?: string[] | null;
}

export interface StageZeroTable {
  hard?: GateRow[];
  soft?: GateRow[];
}

export interface MetricEntry {
  metric: string;
  value: number | string | null;
  unit?: string;
  period?: string;
  source_doc_id?: string;
  page_or_section?: string;
  quote?: string;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface EvidenceEntry {
  intent?: string;
  document_id?: string;
  document_type?: string;
  excerpt?: string;
  url?: string;
}

export interface ReverseDCFBlock {
  wacc?: {
    point: number | null;
    band: [number, number] | null;
    cost_of_equity?: number | null;
    cost_of_debt_after_tax?: number | null;
    weights?: Record<string, number> | null;
    inputs?: Record<string, number | string | null> | null;
  } | null;
  terminal_growth?: {
    value: number | null;
    inputs?: Record<string, number | null> | null;
  } | null;
  hurdle?: {
    value: number | null;
    details?: Record<string, unknown> | null;
  } | null;
  base_irr?: number | null;
  scenarios?: Array<{ name: string; fcf_path: number[]; irr: number | null }>;
  sensitivity?: Record<string, number | null>;
  price?: number | null;
  shares?: number | null;
  net_debt?: number | null;
  ttm_fcf?: number | null;
  fcf_paths?: Record<string, number[]>;
  notes?: string;
}

export interface FinalGateSection {
  definition?: string;
  evidence?: string;
  pass_fail?: string;
}

export type FinalGate = Record<string, FinalGateSection>;

export interface DeltaEntry {
  current: number;
  qoq: number;
  yoy: number;
  qoq_percent: number;
  yoy_percent: number;
}

export interface TriggerAlert {
  trigger?: string;
  message?: string;
  status?: string;
  days_remaining?: number;
  threshold?: number;
  value?: number;
  deadline?: string;
  comparison?: string;
}

export interface AnalystDossier {
  output_0: string;
  stage_0?: StageZeroTable | GateRow[];
  stage_1?: string;
  reverse_dcf?: ReverseDCFBlock;
  final_gate?: FinalGate;
  metrics?: MetricEntry[];
  provenance?: MetricEntry[];
  evidence?: EvidenceEntry[];
  path_reasons?: string[];
  provenance_issues?: string[];
  delta?: Record<string, DeltaEntry>;
  triggers?: TriggerAlert[];
  trigger_alerts?: TriggerAlert[];
}

export interface QAResult {
  status: 'PASS' | 'BLOCKER';
  reasons: string[];
}

export interface ReportPayload {
  analyst: AnalystDossier;
  verifier?: QAResult;
  delta?: Record<string, DeltaEntry>;
  triggers?: TriggerAlert[];
  trigger_alerts?: TriggerAlert[];
}

export interface AppProps {
  initialPayload?: ReportPayload;
  initialTicker?: string;
}
