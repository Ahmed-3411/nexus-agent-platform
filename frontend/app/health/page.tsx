"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell, PageHeader } from "@/components/app-shell";
import { Icons } from "@/components/icons";
import { api } from "@/lib/api";

export default function HealthPage() {
  const [state, setState] = useState<"checking" | "healthy" | "offline">("checking");
  const [latency, setLatency] = useState<number | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const check = useCallback(async () => {
    setState("checking");
    const started = performance.now();
    try { const result = await api.health(); setLatency(performance.now() - started); setState(result.status === "ok" ? "healthy" : "offline"); }
    catch { setLatency(null); setState("offline"); }
    setCheckedAt(new Date());
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => void check(), 0); return () => window.clearTimeout(timer); }, [check]);

  const healthy = state === "healthy";
  const offline = state === "offline";

  return (
    <AppShell>
      <PageHeader eyebrow="Platform status" title="A simple signal for a complex system." description="Live connectivity and response timing from the core backend health endpoint." actions={<button onClick={() => void check()} disabled={state === "checking"} className="btn-secondary"><Icons.refresh className={`h-4 w-4 ${state === "checking" ? "animate-spin" : ""}`} />Check now</button>} />
      <section className="relative overflow-hidden rounded-[34px] bg-[#0F1F3D] p-7 text-white shadow-soft sm:p-10 lg:p-12">
        <div className={`pointer-events-none absolute -right-20 -top-24 h-96 w-96 rounded-full blur-3xl ${healthy ? "bg-emerald-500/25" : offline ? "bg-rose-500/25" : "bg-blue/25"}`} />
        <div className="relative flex flex-col gap-10 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center"><div className={`relative grid h-20 w-20 shrink-0 place-items-center rounded-3xl ${healthy ? "bg-emerald-400 text-emerald-950" : offline ? "bg-rose-400 text-rose-950" : "bg-brand text-white"}`}><Icons.pulse className="h-8 w-8" />{healthy && <span className="absolute -right-1 -top-1 h-4 w-4 rounded-full border-[3px] border-[#0F1F3D] bg-emerald-300" />}</div><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-slate-500">Backend API</p><h2 className="mt-2 text-4xl font-semibold capitalize tracking-[-.04em]">{state}</h2><p className="mt-3 max-w-lg text-sm leading-6 text-slate-400">{healthy ? "All core API services are responding normally." : offline ? "The health endpoint could not be reached. Check backend availability and networking." : "Contacting the health endpoint…"}</p>{healthy && <div className="mt-4 flex flex-wrap gap-2"><span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[.12em] text-emerald-200">Live probe</span><span className="rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[.12em] text-slate-300">Core API</span></div>}</div></div>
          <div className="rounded-3xl border border-white/10 bg-white/[0.05] px-6 py-5 backdrop-blur"><p className="text-[10px] uppercase tracking-[.15em] text-slate-500">Availability signal</p><p className={`mt-2 text-sm font-semibold ${healthy ? "text-emerald-300" : offline ? "text-rose-300" : "text-cyan-200"}`}>{healthy ? "Operational" : offline ? "Action required" : "In progress"}</p></div>
        </div>
      </section>
      <section className="mt-6 grid gap-4 md:grid-cols-3"><HealthMetric label="Endpoint" value="GET /health" caption="Core service probe" /><HealthMetric label="Round trip" value={latency === null ? "—" : `${latency.toFixed(0)} ms`} caption="Browser to API" /><HealthMetric label="Last checked" value={checkedAt ? checkedAt.toLocaleTimeString() : "—"} caption="Local browser time" /></section>
      <section className="panel mt-6 flex flex-col gap-5 p-6 sm:flex-row sm:items-center"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-brandSoft text-brand"><Icons.layers className="h-5 w-5" /></span><div><h3 className="text-sm font-semibold text-slate-700">Scope of this check</h3><p className="mt-1 text-sm leading-6 text-slate-500">This signal confirms API availability. External LLM, Gmail, Drive, and database-provider availability are validated when their workflow tools run.</p></div></section>
    </AppShell>
  );
}

function HealthMetric({ label, value, caption }: { label: string; value: string; caption: string }) {
  return <article className="panel p-6"><p className="section-label">{label}</p><p className="mt-4 font-mono text-xl font-semibold tracking-tight text-ink">{value}</p><p className="mt-1 text-xs text-slate-400">{caption}</p></article>;
}
