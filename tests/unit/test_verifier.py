"""Unit tests for agents.verifier.verify_result."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.verifier import verify_result  # noqa: E402


class TestBasicPassFailCases:
    def test_fails_when_error_present(self):
        record = verify_result("drive.search", {"count": 1, "files": [1]}, "connection timed out")
        assert record["passed"] is False
        assert record["actual"] == "connection timed out"

    def test_fails_when_result_is_none_and_no_error(self):
        record = verify_result("drive.search", None, None)
        assert record["passed"] is False

    def test_unknown_tool_falls_back_to_basic_presence_check(self):
        record = verify_result("some.unmapped.tool", {"anything": True}, None)
        assert record["passed"] is True

    def test_error_takes_precedence_over_a_present_result(self):
        record = verify_result("drive.search", {"count": 1, "files": [1]}, "some error")
        assert record["passed"] is False


class TestCountMatchesListRules:
    def test_database_query_passes_when_counts_match(self):
        result = {"row_count": 2, "rows": [{"id": 1}, {"id": 2}], "truncated": False}
        record = verify_result("database.query", result, None)
        assert record["passed"] is True
        assert record["expected"] == 2
        assert record["actual"] == 2

    def test_database_query_fails_when_counts_mismatch(self):
        result = {"row_count": 142, "rows": [{"id": i} for i in range(139)], "truncated": False}
        record = verify_result("database.query", result, None)
        assert record["passed"] is False
        assert record["expected"] == 142
        assert record["actual"] == 139

    def test_gmail_search_passes_when_counts_match(self):
        result = {"count": 3, "message_ids": ["a", "b", "c"]}
        record = verify_result("gmail.search", result, None)
        assert record["passed"] is True

    def test_drive_search_fails_when_files_list_missing(self):
        result = {"count": 5}
        record = verify_result("drive.search", result, None)
        assert record["passed"] is False
        assert record["actual"] is None


class TestRequiredKeysRules:
    def test_gmail_send_passes_with_message_and_thread_id(self):
        result = {"message_id": "m1", "thread_id": "t1"}
        record = verify_result("gmail.send", result, None)
        assert record["passed"] is True

    def test_gmail_send_fails_without_message_id(self):
        result = {"thread_id": "t1"}
        record = verify_result("gmail.send", result, None)
        assert record["passed"] is False
        assert "message_id" in record["notes"]

    def test_gmail_draft_passes_with_draft_and_message_id(self):
        result = {"draft_id": "d1", "message_id": "m1"}
        record = verify_result("gmail.draft", result, None)
        assert record["passed"] is True


class TestNonDictResult:
    def test_non_dict_result_fails_when_rule_exists(self):
        record = verify_result("database.query", "not a dict", None)
        assert record["passed"] is False
        assert record["actual"] == "str"

    def test_non_dict_result_passes_for_unmapped_tool(self):
        record = verify_result("some.unmapped.tool", "a plain string result", None)
        assert record["passed"] is True
