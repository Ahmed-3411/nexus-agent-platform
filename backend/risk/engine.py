"""
Risk Engine.

Converts a tool's risk_level into:
  1. A numeric score (0.0-1.0), for display/audit purposes and future
     fine-grained scoring (e.g. adjusting a base score up for bulk
     operations — "send to 2,500 customers" vs "send to 1 customer").
  2. A routing decision: what should happen next.

Decision table (mirrors the original project brief):
    LOW      -> AUTO           run immediately, no special logging
    MEDIUM   -> AUTO_WITH_LOG  run immediately, but flag for audit review
    HIGH     -> REQUIRE_APPROVAL   pause for a human decision
    CRITICAL -> REQUIRE_EXPLICIT_AUTH  pause; needs an explicit, named
                                        authorization (stronger than a
                                        plain approve/reject click —
                                        Phase 5 will define what that
                                        means in the dashboard)

This is intentionally decoupled from the Policy Engine: PolicyEngine
answers "is this role allowed to use this tool at all?", RiskEngine
answers "given that it's allowed, how should this specific execution be
handled?". agents/graph.py's risk_check_node currently only checks
requires_approval directly from the tool catalog (Phase 2); routing it
through RiskEngine.decide() is equivalent for now since requires_approval
is itself derived from risk_level, but doing so explicitly is what
Phase 4/5 will build on for bulk-operation score adjustments.
"""
from typing import Literal, TypedDict

from agents.state import RiskLevel

RiskDecision = Literal["AUTO", "AUTO_WITH_LOG", "REQUIRE_APPROVAL", "REQUIRE_EXPLICIT_AUTH"]

_BASE_SCORES: dict[RiskLevel, float] = {
    "LOW": 0.05,
    "MEDIUM": 0.30,
    "HIGH": 0.65,
    "CRITICAL": 0.95,
}

_DECISIONS: dict[RiskLevel, RiskDecision] = {
    "LOW": "AUTO",
    "MEDIUM": "AUTO_WITH_LOG",
    "HIGH": "REQUIRE_APPROVAL",
    "CRITICAL": "REQUIRE_EXPLICIT_AUTH",
}


class RiskAssessment(TypedDict):
    risk_level: RiskLevel
    score: float
    decision: RiskDecision
    requires_human: bool


class RiskEngine:
    def score(self, risk_level: RiskLevel) -> float:
        if risk_level not in _BASE_SCORES:
            raise ValueError(f"Unknown risk level '{risk_level}'.")
        return _BASE_SCORES[risk_level]

    def decide(self, risk_level: RiskLevel) -> RiskAssessment:
        if risk_level not in _DECISIONS:
            raise ValueError(f"Unknown risk level '{risk_level}'.")
        decision = _DECISIONS[risk_level]
        return RiskAssessment(
            risk_level=risk_level,
            score=self.score(risk_level),
            decision=decision,
            requires_human=decision in ("REQUIRE_APPROVAL", "REQUIRE_EXPLICIT_AUTH"),
        )
