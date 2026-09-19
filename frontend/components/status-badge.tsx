import { titleCase } from "@/lib/format";

const styles: Record<string, string> = {
  SUCCEEDED: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
  FAILED: "bg-rose-50 text-rose-700 ring-rose-600/15",
  AWAITING_APPROVAL: "bg-amber-50 text-amber-700 ring-amber-600/15",
  RUNNING: "bg-brandSoft text-brand ring-brand/15",
  PLANNING: "bg-cyan-50 text-cyan-700 ring-cyan-600/15",
  PENDING: "bg-slate-100 text-slate-600 ring-slate-500/15",
  LOW: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
  MEDIUM: "bg-amber-50 text-amber-700 ring-amber-600/15",
  HIGH: "bg-orange-50 text-orange-700 ring-orange-600/15",
  CRITICAL: "bg-rose-50 text-rose-700 ring-rose-600/15",
  APPROVED: "bg-emerald-50 text-emerald-700 ring-emerald-600/15",
  REJECTED: "bg-rose-50 text-rose-700 ring-rose-600/15",
};

export function StatusBadge({ value }: { value: string }) {
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.11em] ring-1 ring-inset ${styles[value] || styles.PENDING}`}>{titleCase(value)}</span>;
}
