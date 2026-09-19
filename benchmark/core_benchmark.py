"""Dependency-light Phase 7 control-plane benchmark.

Measures deterministic in-process overhead for the platform's policy, risk,
approval decision, verification and recovery logic. It deliberately does NOT
claim to represent production E2E latency because it excludes LangGraph,
Postgres, MCP transports, external SaaS APIs and LLM calls.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agents.recovery import decide_recovery  # noqa: E402
from agents.state import new_workflow_state  # noqa: E402
from agents.verifier import verify_result  # noqa: E402
from policies.engine import PolicyEngine  # noqa: E402
from risk.engine import RiskEngine  # noqa: E402
from metrics import Sample, summarize  # noqa: E402

POLICY = PolicyEngine()
RISK = RiskEngine()


async def _yield() -> None:
    # Introduce a real async scheduling boundary without external I/O so
    # concurrency measurements exercise scheduler/control-plane contention.
    await asyncio.sleep(0)


async def _low_risk(iteration: int, concurrency: int) -> Sample:
    started = time.perf_counter()
    state = new_workflow_state("find quarterly report", role="analyst")
    state["plan"] = [{"step_index": 0, "tool_name": "drive.search", "arguments": {"query": "quarterly report"}}]
    decision = POLICY.evaluate(state["role"], "drive.search")
    assessment = RISK.decide(decision["risk_level"])
    await _yield()
    result = {"count": 1, "files": [{"id": "f1"}]}
    verification = verify_result("drive.search", result, None)
    state["verifications"][0] = verification
    state["status"] = "SUCCEEDED" if decision["allowed"] and not assessment["requires_human"] and verification["passed"] else "FAILED"
    elapsed = (time.perf_counter() - started) * 1000
    return Sample("core_low_risk", concurrency, iteration, elapsed, state["status"] == "SUCCEEDED", state["status"])


async def _approval(iteration: int, concurrency: int) -> Sample:
    started = time.perf_counter()
    state = new_workflow_state("email the customer", role="manager")
    state["plan"] = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "customer@example.com"}}]
    decision = POLICY.evaluate(state["role"], "gmail.send")
    assessment = RISK.decide(decision["risk_level"])
    state["status"] = "AWAITING_APPROVAL" if decision["allowed"] and assessment["requires_human"] else "FAILED"
    pause = time.perf_counter()

    await _yield()
    if state["status"] == "AWAITING_APPROVAL":
        state["approved_steps"].add(0)
        state["status"] = "RUNNING"
        result = {"message_id": "m1", "thread_id": "t1"}
        verification = verify_result("gmail.send", result, None)
        state["verifications"][0] = verification
        state["status"] = "SUCCEEDED" if verification["passed"] else "FAILED"

    ended = time.perf_counter()
    return Sample(
        "core_approval",
        concurrency,
        iteration,
        (ended - started) * 1000,
        state["status"] == "SUCCEEDED",
        state["status"],
        approval_pause_ms=(pause - started) * 1000,
        approval_resume_ms=(ended - pause) * 1000,
    )


async def _policy_denied(iteration: int, concurrency: int) -> Sample:
    started = time.perf_counter()
    state = new_workflow_state("email the customer", role="analyst")
    decision = POLICY.evaluate(state["role"], "gmail.send")
    await _yield()
    state["status"] = "FAILED" if not decision["allowed"] else "RUNNING"
    elapsed = (time.perf_counter() - started) * 1000
    return Sample("core_policy_denied", concurrency, iteration, elapsed, not decision["allowed"], state["status"])


async def _recovery(iteration: int, concurrency: int) -> Sample:
    started = time.perf_counter()
    state = new_workflow_state("query data", role="analyst")
    error = "connection timeout"
    verification = verify_result("database.query", None, error)
    await _yield()
    recovery = decide_recovery(1, error)
    state["status"] = "RUNNING" if recovery == "retry" else "FAILED"
    elapsed = (time.perf_counter() - started) * 1000
    ok = (not verification["passed"]) and recovery == "retry"
    return Sample("core_recovery_transient", concurrency, iteration, elapsed, ok, state["status"])


SCENARIOS = {
    "core_low_risk": _low_risk,
    "core_approval": _approval,
    "core_policy_denied": _policy_denied,
    "core_recovery_transient": _recovery,
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
    samples: list[Sample] = []
    for concurrency in args.concurrency:
        for scenario in args.scenarios:
            samples.extend(await run_group(scenario, args.iterations, concurrency))
    return samples, summarize(samples)


def write_outputs(samples: list[Sample], summary: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "core_raw_samples.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=asdict(samples[0]).keys())
        writer.writeheader()
        writer.writerows(asdict(s) for s in samples)
    with (out_dir / "core_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    with (out_dir / "core_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--iterations", type=int, default=1000)
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
