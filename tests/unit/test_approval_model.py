import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from db.models import Approval  # noqa: E402


def test_approval_model_has_decision_audit_fields():
    columns = Approval.__table__.columns
    assert {"workflow_step_id", "requested_at", "decided_at", "decided_by", "decision", "reason"} <= set(columns.keys())
    assert columns["decision"].nullable is True
    assert columns["decided_at"].nullable is True
