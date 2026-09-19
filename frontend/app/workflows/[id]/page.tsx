"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AppShell, PageHeader } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { Icons } from "@/components/icons";
import { JsonView } from "@/components/json-view";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import { formatDate, shortId, workflowProgress } from "@/lib/format";
import type { Workflow } from "@/lib/types";

export default function WorkflowDetailsPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { role } = useAuth();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [decisionLoading, setDecisionLoading] = useState<"approve" | "reject" | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const loadWorkflow = useCallback(async () => {
    setLoading(true); setError("");
    try { setWorkflow(await api.getWorkflow(id)); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to load the workflow."); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { const timer = window.setTimeout(() => void loadWorkflow(), 0); return () => window.clearTimeout(timer); }, [loadWorkflow]);

  async function decide(decision: "approve" | "reject") {
    setDecisionLoading(decision); setError("");
    try { await api.decideWorkflow(id, decision, reason.trim()); setReason(""); await loadWorkflow(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to record the decision."); }
    finally { setDecisionLoading(null); }
  }

  const canApprove = role === "admin" || role === "manager";
  const progress = workflow ? workflowProgress(workflow.status, workflow.current_step_index, workflow.plan.length) : null;

  return (
    <AppShell>
      <PageHeader eyebrow="Workflow detail" title={workflow ? shortId(workflow.id) : "Workflow details"} description="A complete record of planning, authorization, execution, verification, and human decisions." actions={<><Link href="/dashboard" className="btn-secondary">Back</Link><button className="btn-secondary" onClick={() => void loadWorkflow()} disabled={loading}><Icons.refresh className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />Refresh</button></>} />
      {error && <div role="alert" className="mb-6 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-inset ring-rose-600/10">{error}</div>}

      {loading && !workflow ? <div className="space-y-5">{Array.from({ length: 3 }).map((_, index) => <div key={index} className="panel h-40 animate-pulse bg-white/70" />)}</div> : workflow ? <>
        <section className="relative overflow-hidden rounded-[32px] bg-[#0F1F3D] p-6 text-white shadow-soft sm:p-8 lg:p-10">
          <div className="pointer-events-none absolute -right-20 -top-28 h-80 w-80 rounded-full bg-cyan/18 blur-3xl" /><div className="pointer-events-none absolute -bottom-36 left-1/3 h-72 w-72 rounded-full bg-brand/22 blur-3xl" />
          <div className="relative flex flex-col justify-between gap-8 lg:flex-row lg:items-end"><div className="max-w-3xl"><div className="flex flex-wrap items-center gap-3"><StatusBadge value={workflow.status} /><span className="text-xs capitalize text-slate-400">{workflow.role.replaceAll("_", " ")}</span></div><h2 className="mt-6 text-2xl font-semibold leading-tight tracking-[-.035em] sm:text-3xl">{workflow.user_request}</h2><p className="mt-5 break-all font-mono text-[10px] text-slate-500">{workflow.id}</p></div><div className="min-w-56 rounded-3xl border border-white/10 bg-white/[0.06] p-5 backdrop-blur"><div className="flex items-end justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-slate-500">Current step</p><p className="mt-2 text-3xl font-semibold tabular-nums">{progress?.current} <span className="text-base font-normal text-slate-500">/ {progress?.total}</span></p></div><span className="text-xs font-semibold text-cyan-200">{progress?.percent}%</span></div><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-brand to-cyan" style={{ width: `${progress?.percent || 0}%` }} /></div></div></div>
        </section>

        <section className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Status"><StatusBadge value={workflow.status} /></Info>
          <Info label="Role"><p className="text-sm font-semibold capitalize text-slate-700">{workflow.role.replaceAll("_", " ")}</p></Info>
          <Info label="Created"><p className="text-sm font-semibold text-slate-700">{formatDate(workflow.created_at)}</p></Info>
          <Info label="Last updated"><p className="text-sm font-semibold text-slate-700">{formatDate(workflow.updated_at)}</p></Info>
        </section>

        {workflow.status === "FAILED" && <section className="mt-6 flex items-start gap-4 rounded-[24px] bg-rose-50 p-5 ring-1 ring-inset ring-rose-600/10 sm:p-6"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-rose-600 text-white"><Icons.x className="h-5 w-5" /></span><div><h2 className="font-semibold text-rose-900">Workflow ended with an error</h2><p className="mt-1 text-sm leading-6 text-rose-700">The completed evidence remains available below. Review the affected step and final result for the original failure details.</p></div></section>}

        {workflow.status === "AWAITING_APPROVAL" && <section className="mt-6 overflow-hidden rounded-[28px] bg-amber-50 ring-1 ring-inset ring-amber-600/10"><div className="flex flex-col gap-6 p-6 lg:flex-row lg:items-end lg:justify-between"><div className="max-w-2xl"><div className="flex items-center gap-2 text-amber-800"><Icons.shield className="h-5 w-5" /><h2 className="font-semibold">Human approval required</h2></div><p className="mt-2 text-sm leading-6 text-amber-800/70">Step {(progress?.current || 0)} is paused because its evaluated risk requires a privileged decision.</p></div>{canApprove ? <div className="w-full lg:max-w-xl"><input className="field" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Optional decision reason" /><div className="mt-3 flex gap-3 lg:justify-end"><button onClick={() => void decide("reject")} disabled={Boolean(decisionLoading)} className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-rose-700 shadow-sm disabled:opacity-50"><Icons.x className="h-4 w-4" />{decisionLoading === "reject" ? "Rejecting…" : "Reject"}</button><button onClick={() => void decide("approve")} disabled={Boolean(decisionLoading)} className="inline-flex items-center gap-2 rounded-full bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm disabled:opacity-50"><Icons.check className="h-4 w-4" />{decisionLoading === "approve" ? "Approving…" : "Approve"}</button></div></div> : <div className="rounded-2xl bg-white/70 px-4 py-3 text-xs text-amber-800">Manager or admin role required.</div>}</div></section>}

        <section className="panel mt-6 overflow-hidden">
          <div className="border-b border-line px-6 py-5 sm:px-8"><p className="section-label">Execution plan</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">From intent to verified result</h2></div>
          <div className="p-6 sm:p-8">
            {workflow.plan.length === 0 ? <p className="text-sm text-slate-400">No execution plan was produced.</p> : <div className="space-y-0">{workflow.plan.map((step, index) => {
              const key = String(step.step_index);
              const completed = Object.prototype.hasOwnProperty.call(workflow.results, key);
              const failed = Object.prototype.hasOwnProperty.call(workflow.errors, key);
              const awaiting = workflow.status === "AWAITING_APPROVAL" && workflow.current_step_index === step.step_index;
              return <article key={step.step_index} className="relative grid grid-cols-[42px_minmax(0,1fr)] gap-4 pb-7 last:pb-0 sm:gap-6">{index < workflow.plan.length - 1 && <span className={`absolute left-[20px] top-11 h-[calc(100%-1.25rem)] w-px ${completed ? "bg-emerald-200" : failed ? "bg-rose-200" : "bg-line"}`} />}<span className={`relative z-10 grid h-10 w-10 place-items-center rounded-full text-xs font-bold shadow-sm ${failed ? "bg-rose-600 text-white" : completed ? "bg-emerald-600 text-white" : awaiting ? "bg-amber-500 text-white" : workflow.current_step_index === step.step_index ? "bg-brand text-white shadow-[0_6px_18px_rgba(37,99,235,0.20)]" : "bg-slate-100 text-slate-500"}`}>{failed ? <Icons.x className="h-4 w-4" /> : completed ? <Icons.check className="h-4 w-4" /> : step.step_index + 1}</span><div className={`min-w-0 rounded-3xl border p-5 sm:p-6 ${failed ? "border-rose-200 bg-rose-50/50" : awaiting ? "border-amber-200 bg-amber-50/50" : "border-line bg-white"}`}><div className="flex flex-wrap items-center gap-2"><h3 className="font-mono text-sm font-semibold text-slate-800">{step.tool_name}</h3>{workflow.risk_levels[key] && <StatusBadge value={workflow.risk_levels[key]} />}{awaiting && <StatusBadge value="AWAITING_APPROVAL" />}</div>{step.description && <p className="mt-2 text-sm leading-6 text-slate-500">{step.description}</p>}<div className="mt-5 grid gap-5 xl:grid-cols-2"><DataBlock title="Arguments" value={step.arguments} /><DataBlock title={failed ? "Error" : "Result"} value={failed ? workflow.errors[key] : workflow.results[key]} /></div>{workflow.verifications[key] !== undefined && <div className="mt-5 rounded-2xl border border-line/80 bg-slate-50/65 p-4"><div className="mb-3 flex items-center gap-2"><span className="grid h-6 w-6 place-items-center rounded-full bg-brandSoft text-brand"><Icons.shield className="h-3.5 w-3.5" /></span><p className="section-label">Verification evidence</p></div><JsonView value={workflow.verifications[key]} /></div>}</div></article>;
            })}</div>}
          </div>
        </section>

        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          <section className="panel p-6 sm:p-8"><p className="section-label">Human control</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Approvals</h2><div className="mt-6 space-y-3">{Object.keys(workflow.approvals || {}).length === 0 ? <p className="rounded-2xl bg-canvas p-4 text-sm text-slate-400">No approval records.</p> : Object.entries(workflow.approvals).map(([step, approval]) => <div key={step} className="rounded-2xl border border-line p-4"><div className="flex items-center justify-between"><p className="text-xs font-semibold text-slate-700">Step {Number(step) + 1}</p><StatusBadge value={approval.decision || "PENDING"} /></div>{approval.reason && <p className="mt-3 text-xs leading-5 text-slate-500">{approval.reason}</p>}<p className="mt-2 text-[10px] text-slate-400">{approval.decided_at ? `Decided ${formatDate(approval.decided_at)}` : "Decision pending"}</p></div>)}</div></section>
          <section className="panel p-6 sm:p-8"><p className="section-label">Outcome</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Final result</h2><div className="mt-6"><JsonView value={workflow.final_result} empty="The workflow has not produced a final result." /></div></section>
        </div>
      </> : <div className="panel p-10 text-center text-sm text-slate-400">Workflow unavailable.</div>}
    </AppShell>
  );
}

function Info({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="panel min-w-0 p-5"><p className="section-label mb-2.5">{label}</p>{children}</div>;
}

function DataBlock({ title, value }: { title: string; value: unknown }) {
  return <div className="min-w-0"><p className="section-label mb-2.5">{title}</p><JsonView value={value} /></div>;
}
