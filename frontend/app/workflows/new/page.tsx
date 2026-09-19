"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { AppShell, PageHeader } from "@/components/app-shell";
import { Icons } from "@/components/icons";
import { StatusBadge } from "@/components/status-badge";
import { api, ApiError } from "@/lib/api";
import type { Workflow } from "@/lib/types";

const examples = [
  { label: "Find planning docs", prompt: "Search Drive for the latest quarterly planning documents" },
  { label: "Review accounts", prompt: "Query the customer database for active enterprise accounts" },
  { label: "Draft follow-up", prompt: "Draft a follow-up email summarizing the latest account activity" },
];

const guardrails = [
  { title: "Role enforcement", detail: "Tool access follows your authenticated role." },
  { title: "Risk evaluation", detail: "High-impact steps pause for human review." },
  { title: "Result verification", detail: "Every output is checked after execution." },
];

export default function CreateWorkflowPage() {
  const [request, setRequest] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<Workflow | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!request.trim()) return;
    setLoading(true); setError(""); setCreated(null);
    try { setCreated(await api.createWorkflow(request.trim())); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to create the workflow."); }
    finally { setLoading(false); }
  }

  return (
    <AppShell>
      <PageHeader eyebrow="New execution" title="What should your agent accomplish?" description="Describe the outcome in plain language. Nexus plans the work, applies policy, executes approved tools, and verifies every result." />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="relative overflow-hidden rounded-[32px] border border-white bg-white/90 p-6 shadow-soft sm:p-9">
          <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-gradient-to-br from-brand/12 to-cyan/12 blur-2xl" />
          <form onSubmit={submit} className="relative">
            <div className="mb-7 flex items-start gap-4"><span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-brand text-white shadow-[0_8px_22px_rgba(37,99,235,0.20)]"><Icons.workflow className="h-5 w-5" /></span><div><h2 className="text-lg font-semibold tracking-tight text-ink">Compose a workflow</h2><p className="mt-1 text-sm leading-6 text-slate-500">Be specific about the outcome; permissions come from your signed-in account.</p></div></div>
            <label htmlFor="request" className="section-label mb-3 block">Your request</label>
            <textarea id="request" value={request} onChange={(event) => setRequest(event.target.value)} className="field min-h-56 resize-y border-0 bg-canvas/80 p-6 text-base leading-8 shadow-inner placeholder:text-slate-400 focus:bg-white sm:text-lg" placeholder="Ask the agent to search, inspect, draft, or query…" maxLength={4000} required />
            <div className="mt-3 flex flex-col gap-2 text-[11px] text-slate-400 sm:flex-row sm:items-center sm:justify-between"><span className="inline-flex items-center gap-1.5"><Icons.shield className="h-3.5 w-3.5 text-brand" />Every planned tool call is policy checked</span><div className="flex items-center gap-3"><span className="hidden text-slate-300 sm:inline">Be specific about the outcome, not the implementation</span><span>{request.length} / 4000</span></div></div>
            {error && <div role="alert" className="mt-5 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-inset ring-rose-600/10">{error}</div>}
            {created && <div className="mt-5 flex flex-col gap-4 rounded-2xl bg-emerald-50/80 p-5 ring-1 ring-inset ring-emerald-600/10 sm:flex-row sm:items-center sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-full bg-emerald-600 text-white"><Icons.check className="h-4 w-4" /></span><p className="text-sm font-semibold text-emerald-800">Workflow created</p><StatusBadge value={created.status} /></div><p className="mt-2 font-mono text-[10px] text-emerald-700/60">{created.id}</p></div><Link className="btn-secondary" href={`/workflows/${created.id}`}>View details<Icons.arrow className="h-4 w-4" /></Link></div>}
            <div className="mt-8 flex flex-col-reverse gap-3 border-t border-line pt-7 sm:flex-row sm:justify-end"><Link className="btn-secondary" href="/dashboard">Cancel</Link><button className="btn-primary min-w-44" disabled={loading || !request.trim()}>{loading ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />Executing…</> : <><Icons.plus className="h-4 w-4" />Create workflow</>}</button></div>
          </form>
        </section>

        <aside className="space-y-6">
          <section className="panel p-6"><div className="flex items-end justify-between"><div><p className="section-label">Try an example</p><p className="mt-1 text-xs text-slate-400">Start with a common enterprise task.</p></div><span className="rounded-full bg-brandSoft px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[.12em] text-brand">3 prompts</span></div><div className="mt-4 space-y-2.5">{examples.map((example) => <button key={example.label} type="button" onClick={() => setRequest(example.prompt)} className="group w-full rounded-2xl bg-canvas/70 p-4 text-left transition hover:bg-brandSoft/75"><span className="flex items-center justify-between text-sm font-semibold text-slate-700 group-hover:text-brand">{example.label}<Icons.arrow className="h-4 w-4" /></span><span className="mt-1.5 block text-xs leading-5 text-slate-400">{example.prompt}</span></button>)}</div></section>
          <section className="panel overflow-hidden"><div className="bg-gradient-to-br from-[#102A56] via-[#163A78] to-[#0E7490] p-6 text-white"><Icons.shield className="h-6 w-6 text-cyan-200" /><h2 className="mt-5 text-lg font-semibold">Guardrails are always on.</h2><p className="mt-2 text-sm leading-6 text-slate-300">Security stays embedded from plan to final result.</p></div><div className="space-y-5 p-6">{guardrails.map((item, index) => <div key={item.title} className="flex gap-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brandSoft text-[10px] font-bold text-brand">0{index + 1}</span><div><p className="text-xs font-semibold text-slate-700">{item.title}</p><p className="mt-1 text-xs leading-5 text-slate-400">{item.detail}</p></div></div>)}</div></section>
        </aside>
      </div>
    </AppShell>
  );
}
