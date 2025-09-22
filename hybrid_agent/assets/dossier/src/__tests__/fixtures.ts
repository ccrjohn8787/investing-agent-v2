import { ReportPayload } from '../types';

export const completePayload: ReportPayload = {
  analyst: {
    output_0: 'Mature path. Hard gates: PASS. Final Decision Gate: PASS. WACC=9.0% (8.0%–10.0%), g=3.0%, Hurdle IRR=12.0%.',
    stage_0: {
      hard: [
        {
          gate: 'Circle of Competence',
          result: 'Pass',
          what_it_means: 'Disclosures sufficient',
          pass_rule: 'Revenue > 0',
          metrics_sources: ['DOC-1 | p1 | https://example.com'],
          evidence: ['Segment disclosures consistent with analyst coverage.'],
        },
        {
          gate: 'Valuation',
          result: 'Pass',
          what_it_means: 'ROIC exceeds WACC',
          pass_rule: 'ROIC >= WACC',
          metrics_sources: ['DOC-2 | p2 | https://example.com'],
          evidence: ['Deterministic ROIC above cost of capital.'],
        }
      ],
      soft: [
        {
          gate: 'Industry',
          result: 'Soft-Pass',
          what_it_means: 'Industry backdrop stable',
          pass_rule: 'Monitor TAM and competition',
          flip_trigger: 'Refresh TAM — due 2025-03-31',
          evidence: ['Industry TAM refresh scheduled for H1.'],
        }
      ],
    },
    stage_1: 'Uber continues to scale network density with expanding take rates while maintaining profitability discipline.',
    reverse_dcf: {
      wacc: {
        point: 0.09,
        band: [0.08, 0.1],
        cost_of_equity: 0.103,
        cost_of_debt_after_tax: 0.038,
        weights: { equity: 0.85, debt: 0.15 },
      },
      terminal_growth: { value: 0.03, inputs: { inflation: 0.022, real_gdp: 0.015 } },
      hurdle: { value: 0.12, details: { base: 0.15, adjustment_bps: -300 } },
      base_irr: 0.145,
      scenarios: [
        { name: 'Base', fcf_path: [5.1e9, 5.6e9, 6.1e9, 6.7e9, 7.3e9], irr: 0.145 },
        { name: 'Bull', fcf_path: [5.1e9, 5.8e9, 6.7e9, 7.6e9, 8.8e9], irr: 0.182 },
        { name: 'Bear', fcf_path: [5.1e9, 5.3e9, 5.6e9, 5.8e9, 6.1e9], irr: 0.102 }
      ],
      sensitivity: {
        'wacc+100bps': 0.121,
        'wacc-100bps': 0.168,
        'g+50bps': 0.153,
        'g-50bps': 0.138
      },
      price: 69.0,
      shares: 2.1e9,
      net_debt: 9.0e9,
      ttm_fcf: 5.051e9,
      notes: 'Scenario set derived from deterministic calculator output.',
    },
    final_gate: {
      variant: {
        definition: 'Variant thesis centers on network density and advertising mix. ',
        evidence: 'Execution benefits visible in Stage-1 narrative.',
        pass_fail: 'Watch',
      },
      'price_power': {
        definition: 'Monitor pricing power evidence from evidence section.',
        pass_fail: 'TBD',
      },
      kill_switch: {
        definition: 'Base hurdle: 15%. Hurdle policy adjustment: -150 bps for mature marketplace.',
      }
    },
    metrics: [
      {
        metric: 'WACC-point',
        value: 0.09,
        period: 'TTM-2024Q4',
        source_doc_id: 'MACRO-UBER-VALUATION-2024',
        page_or_section: 'Valuation Inputs',
        quote: 'Risk-free rate (UST10Y) 31-Dec-2024: 4.30%. Damodaran implied ERP Jan-2025: 5.50%.',
        url: 'https://research.hybridagent.local/uber-valuation-2024',
      }
    ],
    evidence: [
      {
        intent: 'pricing_power',
        excerpt: 'Take rates improved 120 bps year over year with minimal churn impact.',
      }
    ],
    path_reasons: ['Segment disclosure < 8 quarters'],
    delta: {
      Revenue: { current: 37000000000, qoq: 1200000000, yoy: 5000000000, qoq_percent: 0.034, yoy_percent: 0.156 },
    },
    triggers: [
      { trigger: 'Mobility Take Rate', threshold: 0.22, comparison: 'gte', deadline: '2025-03-31', message: 'Monitor take rate expansion.' },
    ],
    trigger_alerts: [
      { trigger: 'Mobility Take Rate', message: 'Breach detected for Mobility Take Rate: value 0.20', status: 'BREACH', days_remaining: 45 },
    ],
  },
  verifier: {
    status: 'PASS',
    reasons: [],
  },
  delta: {
    Revenue: { current: 37000000000, qoq: 1200000000, yoy: 5000000000, qoq_percent: 0.034, yoy_percent: 0.156 },
  },
  triggers: [
    { trigger: 'Mobility Take Rate', threshold: 0.22, comparison: 'gte', deadline: '2025-03-31', message: 'Monitor take rate expansion.' },
  ],
  trigger_alerts: [
    { trigger: 'Mobility Take Rate', message: 'Breach detected for Mobility Take Rate: value 0.20', status: 'BREACH', days_remaining: 45 },
  ],
};

export const missingSectionsPayload: ReportPayload = {
  analyst: {
    output_0: 'Emergent path. Hard gates: FAIL. Final Decision Gate: WATCH. WACC=NA, g=NA, Hurdle IRR=NA.',
    delta: {},
    triggers: [],
    trigger_alerts: [],
  },
  verifier: {
    status: 'BLOCKER',
    reasons: ['Missing Valuation gate'],
  },
  delta: {},
  triggers: [],
  trigger_alerts: [],
};
