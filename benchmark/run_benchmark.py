"""Enterprise workflow benchmark for the agent orchestration stack.

The default benchmark is deterministic and offline: planner/tool boundaries
are mocked while the real LangGraph, policy/risk, verification, recovery and
approval routing code executes. This isolates platform overhead from network
and LLM variance. Use --iterations and --concurrency to scale the run.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agents import runner  # noqa: E402


from metrics import Sample, summarize  # noqa: E402


async def _run_low_risk(iteration: int, concurrency: int) -> Sample:
    plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {"query": "quarterly report"}}]
    t0 = time.perf_counter()
    with (
        patch("agents.graph.generate_plan", return_value=plan),
        patch("agents.graph.execute_step", return_value={"count": 1, "files": [{"id": "f1"}]}),
    ):
        _, state = await runner.start_workflow("find quarterly report", role="analyst")
    elapsed = (time.perf_counter() - t0) * 1000
    return Sample("low_risk_e2e", concurrency, iteration, elapsed, state["status"] == "SUCCEEDED", state["status"])


async def _run_approval(iteration: int, concurrency: int) -> Sample:
    plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "customer@example.com"}}]
    t0 = time.perf_counter()
    with patch("agents.graph.generate_plan", return_value=plan):
        workflow_id, paused = await runner.start_workflow("email the customer", role="manager")
    t_pause = time.perf_counter()
    with patch("agents.graph.execute_step", return_value={"message_id": "m1", "thread_id": "t1"}):
        final = await runner.approve_step(workflow_id, approve=True)
    t_end = time.perf_counter()
    return Sample(
        "approval_e2e",
        concurrency,
        iteration,
        (t_end - t0) * 1000,
        paused["status"] == "AWAITING_APPROVAL" and final["status"] == "SUCCEEDED",
        final["status"],
        approval_pause_ms=(t_pause - t0) * 1000,
        approval_resume_ms=(t_end - t_pause) * 1000,
    )


async def _run_policy_denied(iteration: int, concurrency: int) -> Sample:
    plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "customer@example.com"}}]
    t0 = time.perf_counter()
    with patch("agents.graph.generate_plan", return_value=plan):
        _, state = await runner.start_workflow("email the customer", role="analyst")
    elapsed = (time.perf_counter() - t0) * 1000
    ok = state["status"] == "FAILED" and "Policy denied" in state.get("errors", {}).get(0, "")
    return Sample("policy_denied", concurrency, iteration, elapsed, ok, state["status"])


SCENARIOS = {
    "low_risk_e2e": _run_low_risk,
    "approval_e2e": _run_approval,
    "policy_denied": _run_policy_denied,
}


async def run_group(name: str, iterations: int, concurrency: int) -> list[Sample]:
    fn = SCENARIOS[name]
    semaphore = asyncio.Semaphore(concurrency)

    async def one(i: int) -> Sample:
        async with semaphore:
            return await fn(i, concurrency)

    group_started = time.perf_counter()
    samples = await asyncio.gather(*(one(i) for i in range(iterations)))
    group_elapsed_ms = (time.perf_counter() - group_started) * 1000
    for sample in samples:
        sample.group_elapsed_ms = group_elapsed_ms
    return samples


async def main_async(args: argparse.Namespace) -> tuple[list[Sample], list[dict]]:
    runner._workflow_store.clear()
    samples: list[Sample] = []
    for concurrency in args.concurrency:
        for scenario in args.scenarios:
            samples.extend(await run_group(scenario, args.iterations, concurrency))
    return samples, summarize(samples)


def write_outputs(samples: list[Sample], summary: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "raw_samples.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=asdict(samples[0]).keys())
        writer.writeheader()
        writer.writerows(asdict(s) for s in samples)
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    with (out_dir / "summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--iterations", type=int, default=100)
    p.add_argument("--concurrency", type=int, nargs="+", default=[1, 5, 10, 25])
    p.add_argument("--scenarios", nargs="+", choices=sorted(SCENARIOS), default=list(SCENARIOS))
    p.add_argument("--output", type=Path, default=ROOT / "benchmark" / "results")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    samples, summary = asyncio.run(main_async(args))
    write_outputs(samples, summary, args.output)
    print(json.dumps(summary, indent=2))
    if any(row["success_rate"] < 1.0 for row in summary):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
