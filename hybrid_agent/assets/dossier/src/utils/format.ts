export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'NA';
  }
  const absValue = Math.abs(value);
  if (absValue >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (absValue >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (absValue >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString();
};

export const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'NA';
  }
  return `${(value * 100).toFixed(1)}%`;
};

export const formatNumber = (value: number | string | null | undefined): string => {
  if (value === null || value === undefined) {
    return 'NA';
  }
  if (typeof value === 'string') {
    return value;
  }
  return value.toLocaleString();
};

export const formatBand = (band: [number, number] | null | undefined): string => {
  if (!band) {
    return 'NA';
  }
  const [low, high] = band;
  if (low === null || high === null) {
    return 'NA';
  }
  return `${formatPercent(low)} – ${formatPercent(high)}`;
};
