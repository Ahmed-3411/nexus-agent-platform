"use client";

import { useMemo, useState } from "react";
import { AppShell, PageHeader } from "@/components/app-shell";
import { stackResults, syntheticResults } from "@/data/benchmark";
import { formatMetric, titleCase } from "@/lib/format";
import type { BenchmarkResult } from "@/lib/types";

const scenarios = ["denied_path", "read_path", "approval_path"] as const;
const scenarioLabels = { denied_path: "Policy denied", read_path: "Normal read / tool", approval_path: "Approval workflow" };

export default function BenchmarkPage() {
  const [mode, setMode] = useState<"stack" | "synthetic">("stack");
  const [scenario, setScenario] = useState<(typeof scenarios)[number]>("read_path");
  const results = mode === "stack" ? stackResults : syntheticResults;
  const selected = useMemo(() => results.filter((item) => item.scenario === scenario).sort((a, b) => a.concurrency - b.concurrency), [results, scenario]);
  const peak = selected[selected.length - 1];

  return (
    <AppShell>
      <PageHeader eyebrow="Phase 7 validation" title="Performance, without the ambiguity." description="Compare measured orchestration performance with modeled latency budgets across four concurrency levels." />

      <section className="grid gap-4 lg:grid-cols-2">
        <ModeCard active={mode === "stack"} onClick={() => setMode("stack")} label="Real stack" title="Measured orchestration stack" description="Real LangGraph, policy, risk, approval, verification, recovery, deterministic planning, and MCP boundaries." tone="blue" />
        <ModeCard active={mode === "synthetic"} onClick={() => setMode("synthetic")} label="Synthetic model" title="Latency budget simulation" description="Modeled component delays for budget validation. These values are explicitly separate from measured stack performance." tone="cyan" />
      </section>

      <div className="my-7 flex flex-wrap gap-2 rounded-2xl bg-white/60 p-2 ring-1 ring-inset ring-white">{scenarios.map((item) => <button key={item} onClick={() => setScenario(item)} className={`rounded-xl px-4 py-2.5 text-xs font-semibold transition ${scenario === item ? "bg-brand text-white shadow-[0_6px_18px_rgba(37,99,235,0.18)]" : "text-slate-500 hover:bg-white hover:text-brand"}`}>{scenarioLabels[item]}</button>)}</div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="p50 latency" value={`${formatMetric(peak.p50_ms, 2)} ms`} />
        <Metric label="p95 latency" value={`${formatMetric(peak.p95_ms, 2)} ms`} />
        <Metric label="p99 latency" value={`${formatMetric(peak.p99_ms, 2)} ms`} />
        <Metric label="Mean latency" value={`${formatMetric(peak.mean_ms, 2)} ms`} />
        <Metric label="Throughput" value={`${formatMetric(peak.throughput_ops_s, 1)} ops/s`} caption={`${(peak.success_rate * 100).toFixed(0)}% success · C=${peak.concurrency}`} />
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px]">
        <section className="panel p-6 sm:p-8"><div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><div><p className="section-label">Tail latency</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Performance by concurrency</h2><p className="mt-1 text-xs text-slate-400">{scenarioLabels[scenario]} · milliseconds · 500 samples per level</p></div><span className={`self-start rounded-full px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.13em] ${mode === "stack" ? "bg-brandSoft text-brand" : "bg-cyan-50 text-cyan-700"}`}>{mode === "stack" ? "Measured" : "Synthetic"}</span></div><LatencyChart data={selected} /></section>
        <section className="panel overflow-hidden"><div className="border-b border-line px-6 py-5"><p className="section-label">Profile</p><h2 className="mt-2 text-lg font-semibold tracking-tight text-ink">Concurrency detail</h2></div><div className="overflow-x-auto"><table className="w-full text-left"><thead className="border-b border-line bg-slate-50/70 text-[9px] uppercase tracking-[.12em] text-slate-400"><tr><th className="px-5 py-3">C</th><th className="px-4 py-3">Mean</th><th className="px-4 py-3">p99</th><th className="px-4 py-3">Ops/s</th><th className="px-4 py-3">Success</th></tr></thead><tbody className="divide-y divide-line/80">{selected.map((item) => <tr key={item.concurrency} className="text-xs hover:bg-slate-50/60"><td className="px-5 py-4 font-bold text-blue">{item.concurrency}</td><td className="px-4 py-4 text-slate-500">{formatMetric(item.mean_ms, 2)}</td><td className="px-4 py-4 text-slate-500">{formatMetric(item.p99_ms, 2)}</td><td className="px-4 py-4 text-slate-500">{formatMetric(item.throughput_ops_s, 1)}</td><td className="px-4 py-4 font-semibold text-emerald-600">{(item.success_rate * 100).toFixed(0)}%</td></tr>)}</tbody></table></div></section>
      </div>

      <section className="panel mt-6 overflow-hidden"><div className="flex flex-col justify-between gap-3 border-b border-line px-6 py-5 sm:flex-row sm:items-center sm:px-8"><div><p className="section-label">Complete dataset</p><h2 className="mt-2 text-lg font-semibold tracking-tight text-ink">{mode === "stack" ? "Real-stack measurements" : "Synthetic simulation results"}</h2></div><p className="text-xs text-slate-400">p50, p95, p99, mean, throughput, success</p></div><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left"><thead className="border-b border-line bg-slate-50/70 text-[9px] uppercase tracking-[.13em] text-slate-400"><tr><th className="px-6 py-3.5">Scenario</th><th className="px-5 py-3.5">Concurrency</th><th className="px-5 py-3.5">p50 ms</th><th className="px-5 py-3.5">p95 ms</th><th className="px-5 py-3.5">p99 ms</th><th className="px-5 py-3.5">Mean ms</th><th className="px-5 py-3.5">Throughput</th><th className="px-5 py-3.5">Success</th></tr></thead><tbody className="divide-y divide-line/70">{results.map((item) => <tr key={`${item.scenario}-${item.concurrency}`} className="text-xs hover:bg-slate-50/60"><td className="px-6 py-4 font-semibold text-slate-700">{scenarioLabels[item.scenario]}</td><td className="px-5 py-4 font-semibold text-blue">{item.concurrency}</td><td className="px-5 py-4 text-slate-500">{formatMetric(item.p50_ms, 3)}</td><td className="px-5 py-4 text-slate-500">{formatMetric(item.p95_ms, 3)}</td><td className="px-5 py-4 text-slate-600">{formatMetric(item.p99_ms, 3)}</td><td className="px-5 py-4 text-slate-500">{formatMetric(item.mean_ms, 3)}</td><td className="px-5 py-4 text-slate-600">{formatMetric(item.throughput_ops_s, 2)} ops/s</td><td className="px-5 py-4 font-semibold text-emerald-600">{(item.success_rate * 100).toFixed(0)}%</td></tr>)}</tbody></table></div></section>
    </AppShell>
  );
}

function ModeCard({ active, onClick, label, title, description, tone }: { active: boolean; onClick: () => void; label: string; title: string; description: string; tone: "blue" | "cyan" }) {
  const gradient = tone === "blue" ? "from-brand/14 via-brandSoft/80 to-white" : "from-cyan/14 via-cyan-50/70 to-white";
  return <button onClick={onClick} className={`group relative overflow-hidden rounded-[28px] border p-6 text-left transition-all duration-200 sm:p-7 ${active ? "border-brand/10 bg-white shadow-[0_18px_55px_rgba(18,24,38,0.07)]" : "border-line/70 bg-white/70 hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_16px_42px_rgba(18,24,38,0.05)]"}`}><div className={`absolute inset-0 bg-gradient-to-br ${gradient} ${active ? "opacity-100" : "opacity-35"}`} /><div className={`absolute inset-x-0 top-0 h-1 ${tone === "blue" ? "bg-brand" : "bg-cyan"} ${active ? "opacity-100" : "opacity-0"}`} /><div className="relative"><div className="flex items-center justify-between"><span className={`rounded-full bg-white/80 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.15em] shadow-sm ${tone === "blue" ? "text-brand" : "text-cyan-700"}`}>{label}</span><span className={`grid h-6 w-6 place-items-center rounded-full border ${active ? "border-brand bg-brand" : "border-slate-300 bg-white"}`}>{active && <span className="h-2 w-2 rounded-full bg-white" />}</span></div><h2 className="mt-6 text-xl font-semibold tracking-tight text-ink">{title}</h2><p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">{description}</p></div></button>;
}

function Metric({ label, value, caption }: { label: string; value: string; caption?: string }) {
  return <article className="panel p-5"><p className="section-label">{label}</p><p className="mt-4 text-xl font-semibold tracking-[-.03em] text-ink">{value}</p>{caption && <p className="mt-2 text-[10px] text-slate-400">{caption}</p>}</article>;
}

function LatencyChart({ data }: { data: BenchmarkResult[] }) {
  const width = 720, height = 270, left = 48, right = 20, top = 20, bottom = 38;
  const chartWidth = width - left - right, chartHeight = height - top - bottom;
  const max = Math.max(...data.map((item) => item.p99_ms)) * 1.12;
  const x = (index: number) => left + (index * chartWidth) / (data.length - 1);
  const y = (value: number) => top + chartHeight - (value / max) * chartHeight;
  const series = [{ key: "p50_ms", label: "p50", color: "#2563EB" }, { key: "p95_ms", label: "p95", color: "#22C7D6" }, { key: "p99_ms", label: "p99", color: "#F4B740" }] as const;
  return <div><svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Latency percentiles by concurrency"><defs><linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#2563EB" stopOpacity=".12"/><stop offset="1" stopColor="#2563EB" stopOpacity="0"/></linearGradient></defs>{[0, .25, .5, .75, 1].map((part) => { const yy = top + chartHeight * part; return <g key={part}><line x1={left} y1={yy} x2={width - right} y2={yy} stroke="#e6e9f0" strokeDasharray="3 5"/><text x={left - 9} y={yy + 3} textAnchor="end" fill="#94a3b8" fontSize="9">{formatMetric(max * (1 - part), 0)}</text></g>; })}{data.map((item, index) => <g key={item.concurrency}><line x1={x(index)} y1={top} x2={x(index)} y2={top + chartHeight} stroke="#eef0f4"/><text x={x(index)} y={height - 12} textAnchor="middle" fill="#94a3b8" fontSize="10">C={item.concurrency}</text></g>)}<path d={`M ${x(0)} ${y(data[0].p50_ms)} ${data.slice(1).map((item, index) => `L ${x(index + 1)} ${y(item.p50_ms)}`).join(" ")} L ${x(data.length - 1)} ${top + chartHeight} L ${x(0)} ${top + chartHeight} Z`} fill="url(#chartFill)"/>{series.map((line) => { const points = data.map((item, index) => `${x(index)},${y(item[line.key])}`).join(" "); return <g key={line.key}><polyline points={points} fill="none" stroke={line.color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round"/>{data.map((item, index) => <circle key={item.concurrency} cx={x(index)} cy={y(item[line.key])} r="3.5" fill="#fff" stroke={line.color} strokeWidth="2"/>)}</g>; })}</svg><div className="flex justify-center gap-5">{series.map((line) => <div key={line.key} className="flex items-center gap-2 text-[10px] uppercase tracking-[.12em] text-slate-400"><span className="h-0.5 w-5" style={{ backgroundColor: line.color }} />{titleCase(line.label)}</div>)}</div></div>;
}
