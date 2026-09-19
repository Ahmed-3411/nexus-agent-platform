"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell, PageHeader } from "@/components/app-shell";
import { Icons } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import { formatDate, shortId, workflowProgress } from "@/lib/format";
import type { WorkflowSummary } from "@/lib/types";

const accents = {
  blue: "from-brandSoft/95 via-blue-50/60 to-white text-brand",
  amber: "from-amber-100/70 to-orange-50/30 text-amber-600",
  green: "from-emerald-100/70 to-teal-50/30 text-emerald-600",
  rose: "from-rose-100/70 to-pink-50/30 text-rose-600",
};

function StatCard({ label, value, caption, icon: Icon, accent }: { label: string; value: number | string; caption: string; icon: typeof Icons.grid; accent: keyof typeof accents }) {
  return (
    <article className="panel group relative min-h-44 overflow-hidden p-6 hover:-translate-y-0.5 hover:border-brand/10 hover:shadow-[0_20px_55px_rgba(18,24,38,0.08)]">
      <div className={`absolute inset-0 bg-gradient-to-br opacity-75 ${accents[accent]}`} />
      <div className="relative flex h-full flex-col justify-between">
        <div className="flex items-center justify-between"><p className="text-xs font-semibold text-slate-500">{label}</p><span className="grid h-9 w-9 place-items-center rounded-full border border-white/90 bg-white/85 shadow-[0_4px_12px_rgba(18,24,38,0.04)] transition-transform duration-200 group-hover:scale-[1.04]"><Icon className="h-4 w-4" /></span></div>
        <div><p className="mt-8 text-4xl font-semibold tracking-[-.05em] text-ink">{value}</p><p className="mt-1.5 text-xs text-slate-500">{caption}</p></div>
      </div>
    </article>
  );
}

export default function DashboardPage() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [health, setHealth] = useState<"checking" | "healthy" | "offline">("checking");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    const [workflowResult, healthResult] = await Promise.allSettled([api.listWorkflows(), api.health()]);
    if (workflowResult.status === "fulfilled") setWorkflows(workflowResult.value);
    else setError(workflowResult.reason instanceof ApiError ? workflowResult.reason.message : "Could not load workflows.");
    setHealth(healthResult.status === "fulfilled" && healthResult.value.status === "ok" ? "healthy" : "offline");
    setLoading(false);
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => void refresh(), 0); return () => window.clearTimeout(timer); }, [refresh]);

  const counts = useMemo(() => ({
    active: workflows.filter((workflow) => ["PENDING", "PLANNING", "RUNNING"].includes(workflow.status)).length,
    approval: workflows.filter((workflow) => workflow.status === "AWAITING_APPROVAL").length,
    completed: workflows.filter((workflow) => workflow.status === "SUCCEEDED").length,
    failed: workflows.filter((workflow) => workflow.status === "FAILED").length,
  }), [workflows]);

  return (
    <AppShell>
      <PageHeader eyebrow="Operations center" title="Agent operations, at a glance." description="A clear view of every workflow, approval, and system signal across your governed AI workspace." actions={<><button onClick={() => void refresh()} disabled={loading} className="btn-secondary"><Icons.refresh className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />Refresh</button><Link href="/workflows/new" className="btn-primary"><Icons.plus className="h-4 w-4" />New workflow</Link></>} />

      {error && <div className="mb-6 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-inset ring-rose-600/10">{error}</div>}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Active workflows" value={loading ? "—" : counts.active} caption="Moving through the execution graph" icon={Icons.layers} accent="blue" />
        <StatCard label="Awaiting approval" value={loading ? "—" : counts.approval} caption="A human decision is required" icon={Icons.clock} accent="amber" />
        <StatCard label="Completed" value={loading ? "—" : counts.completed} caption="Verified successful outcomes" icon={Icons.check} accent="green" />
        <StatCard label="Failed" value={loading ? "—" : counts.failed} caption="Workflows that need attention" icon={Icons.x} accent="rose" />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_290px]">
        <div className="panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-6 py-5 sm:px-7"><div><h2 className="text-base font-semibold tracking-tight text-ink">Recent activity</h2><p className="mt-1 text-xs text-slate-400">Latest workflow state changes</p></div><span className="rounded-full bg-canvas px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.13em] text-slate-500">{workflows.length} records</span></div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px] text-left">
              <thead className="border-b border-line bg-slate-50/60 text-[10px] uppercase tracking-[.14em] text-slate-400"><tr><th className="px-7 py-3.5 font-semibold">Workflow</th><th className="px-5 py-3.5 font-semibold">Status</th><th className="px-5 py-3.5 font-semibold">Progress</th><th className="px-5 py-3.5 font-semibold">Role</th><th className="px-5 py-3.5 font-semibold">Updated</th><th className="px-5 py-3.5" /></tr></thead>
              <tbody className="divide-y divide-line/80">
                {loading && Array.from({ length: 4 }).map((_, index) => <tr key={index} className="animate-pulse"><td className="px-7 py-5" colSpan={6}><div className="h-4 rounded-full bg-slate-100" /></td></tr>)}
                {!loading && workflows.slice(0, 10).map((workflow) => {
                  const progress = workflowProgress(workflow.status, workflow.current_step_index, workflow.step_count);
                  return <tr key={workflow.id} className="transition-colors duration-150 hover:bg-brandSoft/35">
                    <td className="max-w-sm px-7 py-4"><Link href={`/workflows/${workflow.id}`} className="block"><p className="truncate text-sm font-semibold text-slate-700 hover:text-blue">{workflow.user_request}</p><p className="mt-1 font-mono text-[10px] text-slate-400">{shortId(workflow.id)}</p></Link></td>
                    <td className="px-5 py-4"><StatusBadge value={workflow.status} /></td>
                    <td className="px-5 py-4"><div className="flex items-center gap-3"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue" style={{ width: `${progress.percent}%` }} /></div><span className="text-xs tabular-nums text-slate-500">{progress.current} / {progress.total}</span></div></td>
                    <td className="px-5 py-4 text-xs capitalize text-slate-500">{workflow.role.replaceAll("_", " ")}</td>
                    <td className="px-5 py-4 text-xs text-slate-400">{formatDate(workflow.updated_at)}</td>
                    <td className="px-5 py-4 text-right"><Link href={`/workflows/${workflow.id}`} className="inline-grid h-8 w-8 place-items-center rounded-full text-slate-400 hover:bg-white hover:text-blue hover:shadow-sm" aria-label="Open workflow"><Icons.arrow className="h-4 w-4" /></Link></td>
                  </tr>;
                })}
              </tbody>
            </table>
          </div>
          {!loading && workflows.length === 0 && <div className="relative overflow-hidden px-6 py-14 text-center sm:py-16"><div className="pointer-events-none absolute left-1/2 top-10 h-40 w-72 -translate-x-1/2 rounded-full bg-brandSoft/70 blur-3xl" /><div className="relative mx-auto h-20 w-36"><span className="absolute left-1/2 top-1/2 h-px w-20 -translate-x-1/2 bg-gradient-to-r from-transparent via-brand/30 to-transparent" /><span className="absolute left-5 top-7 h-2.5 w-2.5 rounded-full bg-cyan shadow-[0_0_0_6px_rgba(34,199,214,0.10)]" /><span className="absolute right-5 top-7 h-2.5 w-2.5 rounded-full bg-brand shadow-[0_0_0_6px_rgba(37,99,235,0.10)]" /><div className="absolute left-1/2 top-1/2 grid h-12 w-12 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-2xl border border-brand/10 bg-white text-brand shadow-[0_10px_30px_rgba(37,99,235,0.12)]"><Icons.workflow className="h-5 w-5" /></div></div><p className="relative mt-1 text-sm font-semibold text-slate-700">Your workspace is ready</p><p className="relative mx-auto mt-1 max-w-sm text-xs leading-5 text-slate-400">Create a governed workflow and Nexus will plan, authorize, execute, and verify each step.</p><Link href="/workflows/new" className="btn-primary relative mt-5">Create first workflow</Link></div>}
        </div>

        <aside className="panel flex min-h-64 flex-col justify-between overflow-hidden p-6 hover:border-success/15">
          <div className={`-m-6 mb-7 h-1.5 ${health === "healthy" ? "bg-emerald-400" : health === "offline" ? "bg-rose-400" : "bg-brand"}`} />
          <div><span className={`grid h-12 w-12 place-items-center rounded-2xl ${health === "healthy" ? "bg-emerald-50 text-emerald-600" : health === "offline" ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-brand"}`}><Icons.pulse className="h-5 w-5" /></span><p className="section-label mt-7">System health</p><div className="mt-2 flex items-center gap-2"><h2 className="text-2xl font-semibold capitalize tracking-tight text-ink">{health}</h2>{health === "healthy" && <span className="rounded-full bg-emerald-50 px-2 py-1 text-[9px] font-semibold uppercase tracking-[.13em] text-emerald-700">Live</span>}</div><p className="mt-2 text-sm leading-6 text-slate-500">{health === "healthy" ? "The core API is responding normally." : health === "offline" ? "Backend connectivity needs attention." : "Checking the core API…"}</p><div className="mt-5 grid grid-cols-2 gap-2"><div className="surface-subtle px-3 py-2.5"><p className="text-[9px] font-semibold uppercase tracking-[.12em] text-slate-400">Signal</p><p className="mt-1 text-xs font-semibold text-slate-700">Core API</p></div><div className="surface-subtle px-3 py-2.5"><p className="text-[9px] font-semibold uppercase tracking-[.12em] text-slate-400">Mode</p><p className="mt-1 text-xs font-semibold text-slate-700">Live check</p></div></div></div>
          <Link href="/health" className="mt-7 inline-flex items-center gap-2 text-xs font-semibold text-brand transition-colors hover:text-brandDark">View system status <Icons.arrow className="h-3.5 w-3.5" /></Link>
        </aside>
      </section>
    </AppShell>
  );
}
