export function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function shortId(id: string) {
  return id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}

export function titleCase(value: string) {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatMetric(value: number, digits = 1) {
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function workflowProgress(status: string, currentStepIndex: number, stepCount: number) {
  const total = Math.max(0, stepCount);
  if (total === 0) return { current: 0, total: 0, percent: 0 };

  const rawCurrent = status === "SUCCEEDED" ? total : currentStepIndex + 1;
  const current = Math.min(Math.max(rawCurrent, 1), total);
  return { current, total, percent: Math.round((current / total) * 100) };
}
