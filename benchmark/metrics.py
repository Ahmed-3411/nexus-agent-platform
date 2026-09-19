from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


@dataclass
class Sample:
    scenario: str
    concurrency: int
    iteration: int
    latency_ms: float
    success: bool
    final_status: str
    approval_pause_ms: float | None = None
    approval_resume_ms: float | None = None
    group_elapsed_ms: float | None = None


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def summarize(samples: list[Sample]) -> list[dict]:
    rows: list[dict] = []
    keys = sorted({(s.scenario, s.concurrency) for s in samples})
    for scenario, concurrency in keys:
        group = [s for s in samples if s.scenario == scenario and s.concurrency == concurrency]
        lat = [s.latency_ms for s in group]
        rows.append(
            {
                "scenario": scenario,
                "concurrency": concurrency,
                "n": len(group),
                "success_rate": sum(s.success for s in group) / len(group),
                "mean_ms": statistics.fmean(lat),
                "p50_ms": percentile(lat, 0.50),
                "p95_ms": percentile(lat, 0.95),
                "p99_ms": percentile(lat, 0.99),
                "min_ms": min(lat),
                "max_ms": max(lat),
                "group_elapsed_ms": next((s.group_elapsed_ms for s in group if s.group_elapsed_ms is not None), None),
                "throughput_ops_s": (
                    len(group) / (next((s.group_elapsed_ms for s in group if s.group_elapsed_ms is not None), 0.0) / 1000.0)
                    if next((s.group_elapsed_ms for s in group if s.group_elapsed_ms is not None), 0.0) > 0
                    else None
                ),
            }
        )
    return rows
