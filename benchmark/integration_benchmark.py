"""Phase 7 integration benchmark harness.

Two modes are intentionally separated:

* synthetic: validates concurrency, timing/accounting and layer attribution with
  deterministic async adapters. These numbers are NOT production performance.
* stack: executes the real runner with deterministic planner/tool boundaries;
  requires the full backend dependency stack. It reports blockers instead of
  silently falling back when dependencies are unavailable.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import importlib.util
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

REQUIRED_STACK_MODULES = ("langgraph", "sqlalchemy", "asyncpg", "mcp", "jose")


@dataclass
class LayerSample:
    mode: str
    scenario: str
    concurrency: int
    iteration: int
    success: bool
    final_status: str
    total_ms: float
    orchestration_ms: float = 0.0
    persistence_ms: float = 0.0
    mcp_ms: float = 0.0
    provider_ms: float = 0.0
    approval_ms: float = 0.0
    group_elapsed_ms: float | None = None


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def summarize(samples: list[LayerSample]) -> list[dict]:
    rows: list[dict] = []
    for scenario, concurrency in sorted({(s.scenario, s.concurrency) for s in samples}):
        group = [s for s in samples if s.scenario == scenario and s.concurrency == concurrency]
        total = [s.total_ms for s in group]
        wall = next((s.group_elapsed_ms for s in group if s.group_elapsed_ms is not None), None)
        row = {
            "mode": group[0].mode,
            "scenario": scenario,
            "concurrency": concurrency,
            "n": len(group),
            "success_rate": sum(s.success for s in group) / len(group),
            "mean_ms": statistics.fmean(total),
            "p50_ms": _pct(total, 0.50),
            "p95_ms": _pct(total, 0.95),
            "p99_ms": _pct(total, 0.99),
            "throughput_ops_s": len(group) / (wall / 1000.0) if wall and wall > 0 else None,
        }
        for field in ("orchestration_ms", "persistence_ms", "mcp_ms", "provider_ms", "approval_ms"):
            vals = [getattr(s, field) for s in group]
            row[f"mean_{field}"] = statistics.fmean(vals)
        rows.append(row)
    return rows


async def _delay(ms: float) -> float:
    started = time.perf_counter()
    if ms > 0:
        await asyncio.sleep(ms / 1000.0)
    return (time.perf_counter() - started) * 1000


async def _synthetic_one(scenario: str, iteration: int, concurrency: int, args: argparse.Namespace) -> LayerSample:
    started = time.perf_counter()

    orchestration = await _delay(args.orchestration_ms)
    persistence = await _delay(args.persistence_ms)
    mcp = 0.0
    provider = 0.0
    approval = 0.0

    if scenario in {"read_path", "approval_path"}:
        mcp = await _delay(args.mcp_ms)
        provider = await _delay(args.provider_ms)
    if scenario == "approval_path":
        approval = await _delay(args.approval_ms)
        # Resumed workflows persist their approval decision/final state again.
        persistence += await _delay(args.persistence_ms)

    total = (time.perf_counter() - started) * 1000
    return LayerSample(
        mode="synthetic",
        scenario=scenario,
        concurrency=concurrency,
        iteration=iteration,
        success=True,
        final_status="SUCCEEDED" if scenario != "denied_path" else "FAILED",
        total_ms=total,
        orchestration_ms=orchestration,
        persistence_ms=persistence,
        mcp_ms=mcp,
        provider_ms=provider,
        approval_ms=approval,
    )


async def _stack_one(scenario: str, iteration: int, concurrency: int) -> LayerSample:
    # Imports happen only in stack mode so synthetic mode remains dependency-light.
    from agents import runner

    started = time.perf_counter()
    if scenario == "read_path":
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {"query": "quarterly report"}}]
        with (
            patch("agents.graph.generate_plan", return_value=plan),
            patch("agents.graph.execute_step", return_value={"count": 1, "files": [{"id": "f1"}]}),
        ):
            workflow_id, state = await runner.start_workflow("find quarterly report", role="analyst")
        ok = state["status"] == "SUCCEEDED"
    elif scenario == "approval_path":
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "customer@example.com"}}]
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, paused = await runner.start_workflow("email the customer", role="manager")
        with patch("agents.graph.execute_step", return_value={"message_id": "m1", "thread_id": "t1"}):
            state = await runner.approve_step(workflow_id, approve=True)
        ok = paused["status"] == "AWAITING_APPROVAL" and state["status"] == "SUCCEEDED"
    else:
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "customer@example.com"}}]
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, state = await runner.start_workflow("email the customer", role="analyst")
        ok = state["status"] == "FAILED"

    total = (time.perf_counter() - started) * 1000
    # The process-local store is a runtime cache, not part of the measured
    # result. Bound its size so long benchmark runs do not measure cache growth.
    runner._workflow_store.pop(workflow_id, None)
    return LayerSample(
        mode="stack",
        scenario=scenario,
        concurrency=concurrency,
        iteration=iteration,
        success=ok,
        final_status=state["status"],
        total_ms=total,
        # Stack mode currently measures end-to-end platform overhead. Layer-specific
        # spans become available when running against instrumented real adapters.
        orchestration_ms=total,
    )


def stack_blockers() -> list[str]:
    return [name for name in REQUIRED_STACK_MODULES if importlib.util.find_spec(name) is None]


async def run_group(mode: str, scenario: str, iterations: int, concurrency: int, args: argparse.Namespace) -> list[LayerSample]:
    sem = asyncio.Semaphore(concurrency)

    async def one(i: int) -> LayerSample:
        async with sem:
            if mode == "synthetic":
                return await _synthetic_one(scenario, i, concurrency, args)
            return await _stack_one(scenario, i, concurrency)

    wall_started = time.perf_counter()
    samples = await asyncio.gather(*(one(i) for i in range(iterations)))
    wall_ms = (time.perf_counter() - wall_started) * 1000
    for sample in samples:
        sample.group_elapsed_ms = wall_ms
    return samples


async def main_async(args: argparse.Namespace) -> tuple[list[LayerSample], list[dict]]:
    if args.mode == "stack":
        blockers = stack_blockers()
        if blockers:
            raise RuntimeError("stack mode unavailable; missing modules: " + ", ".join(blockers))

    samples: list[LayerSample] = []
    for concurrency in args.concurrency:
        for scenario in args.scenarios:
            samples.extend(await run_group(args.mode, scenario, args.iterations, concurrency, args))
    return samples, summarize(samples)


def write_outputs(samples: list[LayerSample], summary: list[dict], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    prefix = samples[0].mode
    with (output / f"integration_{prefix}_raw.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=asdict(samples[0]).keys())
        writer.writeheader()
        writer.writerows(asdict(s) for s in samples)
    with (output / f"integration_{prefix}_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    with (output / f"integration_{prefix}_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("synthetic", "stack"), default="synthetic")
    p.add_argument("--iterations", type=int, default=100)
    p.add_argument("--concurrency", type=int, nargs="+", default=[1, 5, 10, 25])
    p.add_argument("--scenarios", nargs="+", choices=("read_path", "approval_path", "denied_path"), default=["read_path", "approval_path", "denied_path"])
    p.add_argument("--orchestration-ms", type=float, default=0.2)
    p.add_argument("--persistence-ms", type=float, default=2.0)
    p.add_argument("--mcp-ms", type=float, default=5.0)
    p.add_argument("--provider-ms", type=float, default=15.0)
    p.add_argument("--approval-ms", type=float, default=10.0)
    p.add_argument("--output", type=Path, default=ROOT / "benchmark" / "results")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        samples, summary = asyncio.run(main_async(args))
    except RuntimeError as exc:
        print(json.dumps({"mode": args.mode, "status": "BLOCKED", "reason": str(exc)}, indent=2))
        raise SystemExit(3) from exc
    write_outputs(samples, summary, args.output)
    print(json.dumps(summary, indent=2))
    if any(row["success_rate"] < 1.0 for row in summary):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
