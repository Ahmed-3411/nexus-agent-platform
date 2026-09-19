"""Unit tests for risk.engine.RiskEngine."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from risk.engine import RiskEngine  # noqa: E402


class TestRiskEngineScore:
    def setup_method(self):
        self.engine = RiskEngine()

    @pytest.mark.parametrize(
        "risk_level,expected",
        [("LOW", 0.05), ("MEDIUM", 0.30), ("HIGH", 0.65), ("CRITICAL", 0.95)],
    )
    def test_scores_match_expected_values(self, risk_level, expected):
        assert self.engine.score(risk_level) == expected

    def test_unknown_risk_level_raises(self):
        with pytest.raises(ValueError):
            self.engine.score("NOT_A_LEVEL")

    def test_scores_are_monotonically_increasing(self):
        levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        scores = [self.engine.score(lvl) for lvl in levels]
        assert scores == sorted(scores)


class TestRiskEngineDecide:
    def setup_method(self):
        self.engine = RiskEngine()

    def test_low_is_fully_automatic(self):
        result = self.engine.decide("LOW")
        assert result["decision"] == "AUTO"
        assert result["requires_human"] is False

    def test_medium_is_automatic_but_logged(self):
        result = self.engine.decide("MEDIUM")
        assert result["decision"] == "AUTO_WITH_LOG"
        assert result["requires_human"] is False

    def test_high_requires_approval(self):
        result = self.engine.decide("HIGH")
        assert result["decision"] == "REQUIRE_APPROVAL"
        assert result["requires_human"] is True

    def test_critical_requires_explicit_auth(self):
        result = self.engine.decide("CRITICAL")
        assert result["decision"] == "REQUIRE_EXPLICIT_AUTH"
        assert result["requires_human"] is True

    def test_result_includes_score_and_level(self):
        result = self.engine.decide("HIGH")
        assert result["risk_level"] == "HIGH"
        assert result["score"] == 0.65
