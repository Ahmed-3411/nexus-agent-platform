"""
Unit tests for audit.logger.build_audit_entries and log_audit_entries.

The pure builder/logger behavior is covered here. Database-backed audit
persistence is exercised by the approval recovery integration tests.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.state import new_workflow_state  # noqa: E402
from audit.logger import build_audit_entries, log_audit_entries  # noqa: E402


def _plan(*tool_names):
    return [
        {"step_index": i, "tool_name": name, "arguments": {"n": i}} for i, name in enumerate(tool_names)
    ]


class TestBuildAuditEntries:
    def test_successful_step_is_recorded_as_success(self):
        state = new_workflow_state("x", role="admin")
        state["plan"] = _plan("drive.search")
        state["risk_levels"] = {0: "LOW"}
        state["results"] = {0: {"count": 0, "files": []}}
        state["step_latency_ms"] = {0: 42}

        entries = build_audit_entries("wf-1", state)

        assert len(entries) == 1
        entry = entries[0]
        assert entry["result"] == "SUCCESS"
        assert entry["tool_name"] == "drive.search"
        assert entry["risk_level"] == "LOW"
        assert entry["latency_ms"] == 42
        assert entry["permission_code"] == "files.read"
        assert entry["error"] is None

    def test_policy_denied_step_is_recorded_as_denied(self):
        state = new_workflow_state("x", role="analyst")
        state["plan"] = _plan("gmail.send")
        state["risk_levels"] = {0: "HIGH"}
        state["errors"] = {0: "Policy denied: Role 'analyst' lacks required permission 'email.send'."}

        entries = build_audit_entries("wf-2", state)

        assert entries[0]["result"] == "DENIED"
        assert "Policy denied" in entries[0]["error"]

    def test_execution_failure_is_recorded_as_failure(self):
        state = new_workflow_state("x", role="admin")
        state["plan"] = _plan("database.query")
        state["risk_levels"] = {0: "LOW"}
        state["errors"] = {0: "Table 'ghost' does not exist in the public schema."}

        entries = build_audit_entries("wf-3", state)

        assert entries[0]["result"] == "FAILURE"
        assert "does not exist" in entries[0]["error"]

    def test_step_awaiting_approval_is_recorded_as_pending(self):
        state = new_workflow_state("x", role="manager")
        state["plan"] = _plan("gmail.send")
        state["risk_levels"] = {0: "HIGH"}
        # no result, no error yet — run ended paused at AWAITING_APPROVAL

        entries = build_audit_entries("wf-4", state)

        assert entries[0]["result"] == "PENDING"
        assert entries[0]["error"] is None

    def test_multiple_steps_are_all_recorded_in_order(self):
        state = new_workflow_state("x", role="admin")
        state["plan"] = _plan("drive.search", "drive.read")
        state["risk_levels"] = {0: "LOW", 1: "LOW"}
        state["results"] = {0: {"count": 0, "files": []}, 1: {"content": "hi"}}

        entries = build_audit_entries("wf-5", state)

        assert [e["step_index"] for e in entries] == [0, 1]
        assert all(e["result"] == "SUCCESS" for e in entries)

    def test_step_never_reached_by_risk_check_is_not_recorded(self):
        # Only step 0 made it to risk_check (e.g. step 0 failed and the
        # run gave up before step 1 was ever considered).
        state = new_workflow_state("x", role="admin")
        state["plan"] = _plan("drive.search", "drive.read")
        state["risk_levels"] = {0: "LOW"}
        state["errors"] = {0: "connection timed out"}

        entries = build_audit_entries("wf-6", state)

        assert len(entries) == 1
        assert entries[0]["step_index"] == 0

    def test_unmapped_tool_gets_null_permission_code(self):
        state = new_workflow_state("x", role="admin")
        state["plan"] = [{"step_index": 0, "tool_name": "not.a.mapped.tool", "arguments": {}}]
        state["risk_levels"] = {0: "LOW"}
        state["results"] = {0: {"ok": True}}

        entries = build_audit_entries("wf-7", state)

        assert entries[0]["permission_code"] is None


class TestLogAuditEntries:
    def test_emits_one_log_line_per_entry(self, caplog):
        state = new_workflow_state("x", role="admin")
        state["plan"] = _plan("drive.search", "drive.read")
        state["risk_levels"] = {0: "LOW", 1: "LOW"}
        state["results"] = {0: {"count": 0, "files": []}, 1: {"content": "hi"}}

        with caplog.at_level(logging.INFO, logger="eap.audit"):
            entries = log_audit_entries("wf-8", state)

        assert len(entries) == 2
        assert len(caplog.records) == 2
        assert "audit_entry" in caplog.records[0].message

    def test_returns_same_entries_build_audit_entries_would(self):
        state = new_workflow_state("x", role="admin")
        state["plan"] = _plan("drive.search")
        state["risk_levels"] = {0: "LOW"}
        state["results"] = {0: {"count": 0, "files": []}}

        direct = build_audit_entries("wf-9", state)
        logged = log_audit_entries("wf-9", state)

        assert direct == logged
