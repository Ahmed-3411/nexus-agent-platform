from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmark"))

from integration_benchmark import LayerSample, main_async, stack_blockers, summarize


def test_layer_summary_includes_throughput_and_means():
    samples = [
        LayerSample("synthetic", "read_path", 1, 0, True, "SUCCEEDED", 10, 1, 2, 3, 4, 0, 20),
        LayerSample("synthetic", "read_path", 1, 1, True, "SUCCEEDED", 20, 2, 4, 6, 8, 0, 20),
    ]
    row = summarize(samples)[0]
    assert row["success_rate"] == 1.0
    assert row["p50_ms"] == 15
    assert row["throughput_ops_s"] == 100.0
    assert row["mean_persistence_ms"] == 3
    assert row["mean_provider_ms"] == 6


def test_synthetic_mode_runs_without_full_stack():
    args = argparse.Namespace(
        mode="synthetic",
        iterations=3,
        concurrency=[1],
        scenarios=["read_path", "approval_path", "denied_path"],
        orchestration_ms=0,
        persistence_ms=0,
        mcp_ms=0,
        provider_ms=0,
        approval_ms=0,
    )
    samples, summary = asyncio.run(main_async(args))
    assert len(samples) == 9
    assert len(summary) == 3
    assert all(row["success_rate"] == 1.0 for row in summary)


def test_stack_blockers_matches_missing_modules():
    expected = {name for name in ("langgraph", "sqlalchemy", "asyncpg", "mcp", "jose") if importlib.util.find_spec(name) is None}
    assert set(stack_blockers()) == expected
