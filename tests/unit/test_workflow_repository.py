"""
Unit tests for db.workflow_repository._step_status.

The rest of workflow_repository.py issues real SQLAlchemy queries and is
meant for integration testing against a real Postgres instance — see the
module's docstring for why mocking the session isn't attempted here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.state import new_workflow_state  # noqa: E402
from db.workflow_repository import _current_step_index_from_steps, _step_status  # noqa: E402


class TestStepStatus:
    def test_succeeded_when_result_present_without_error(self):
        state = new_workflow_state("x")
        state["results"] = {0: {"ok": True}}
        assert _step_status(0, state) == "SUCCEEDED"

    def test_failed_when_error_present(self):
        state = new_workflow_state("x")
        state["errors"] = {0: "boom"}
        assert _step_status(0, state) == "FAILED"

    def test_failed_takes_precedence_over_a_stale_result(self):
        # Shouldn't normally coexist, but if it does, an error means the
        # step is not considered successful.
        state = new_workflow_state("x")
        state["results"] = {0: {"partial": True}}
        state["errors"] = {0: "boom"}
        assert _step_status(0, state) == "FAILED"

    def test_awaiting_approval_for_the_current_paused_step(self):
        state = new_workflow_state("x")
        state["status"] = "AWAITING_APPROVAL"
        state["current_step_index"] = 0
        assert _step_status(0, state) == "AWAITING_APPROVAL"

    def test_awaiting_approval_does_not_apply_to_other_steps(self):
        state = new_workflow_state("x")
        state["status"] = "AWAITING_APPROVAL"
        state["current_step_index"] = 1
        assert _step_status(0, state) == "PENDING"

    def test_pending_when_nothing_has_happened_yet(self):
        state = new_workflow_state("x")
        assert _step_status(0, state) == "PENDING"


class TestCurrentStepIndexRecovery:
    def test_paused_workflow_recovers_exact_approval_step(self):
        steps = [
            {"step_index": 0, "status": "SUCCEEDED"},
            {"step_index": 1, "status": "AWAITING_APPROVAL"},
            {"step_index": 2, "status": "PENDING"},
        ]
        assert _current_step_index_from_steps("AWAITING_APPROVAL", steps) == 1

    def test_completed_workflow_cursor_is_after_last_step(self):
        steps = [
            {"step_index": 0, "status": "SUCCEEDED"},
            {"step_index": 1, "status": "SUCCEEDED"},
        ]
        assert _current_step_index_from_steps("SUCCEEDED", steps) == 2
