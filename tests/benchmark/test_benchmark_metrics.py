import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmark"))

from metrics import Sample, percentile, summarize  # noqa: E402


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5


def test_summary_groups_by_scenario_and_concurrency():
    samples = [
        Sample("x", 1, 0, 10.0, True, "SUCCEEDED"),
        Sample("x", 1, 1, 20.0, True, "SUCCEEDED"),
    ]
    row = summarize(samples)[0]
    assert row["n"] == 2
    assert row["success_rate"] == 1.0
    assert row["mean_ms"] == 15.0
    assert row["p50_ms"] == 15.0
