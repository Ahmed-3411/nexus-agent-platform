"""Unit tests for agents.recovery."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.recovery import (  # noqa: E402
    MAX_RETRIES,
    backoff_seconds,
    classify_error,
    decide_recovery,
)


class TestClassifyError:
    def test_none_error_is_unknown(self):
        assert classify_error(None) == "unknown"

    def test_timeout_is_transient(self):
        assert classify_error("connection timed out after 30s") == "transient"

    def test_rate_limit_is_transient(self):
        assert classify_error("429 Too Many Requests: rate limit exceeded") == "transient"

    def test_table_does_not_exist_is_permanent(self):
        assert classify_error("Table 'ghost_table' does not exist in the public schema.") == "permanent"

    def test_policy_denial_is_permanent(self):
        assert classify_error("Policy denied: Role 'analyst' lacks required permission.") == "permanent"

    def test_not_read_only_is_permanent(self):
        assert classify_error("NotReadOnlyError: only SELECT statements are permitted") == "permanent"

    def test_unrecognized_message_is_unknown(self):
        assert classify_error("something weird happened") == "unknown"

    def test_case_insensitive_matching(self):
        assert classify_error("CONNECTION TIMED OUT") == "transient"


class TestDecideRecovery:
    def test_retries_transient_errors_below_max(self):
        for attempt in range(MAX_RETRIES):
            assert decide_recovery(attempt, "connection timed out") == "retry"

    def test_gives_up_on_transient_error_at_max(self):
        assert decide_recovery(MAX_RETRIES, "connection timed out") == "give_up"

    def test_gives_up_immediately_on_permanent_error_even_on_first_attempt(self):
        assert decide_recovery(0, "Table 'x' does not exist") == "give_up"

    def test_gives_up_immediately_on_permanent_error_regardless_of_attempt_count(self):
        assert decide_recovery(MAX_RETRIES - 1, "403 forbidden") == "give_up"

    def test_unknown_error_follows_fixed_retry_policy(self):
        assert decide_recovery(0, "something weird happened") == "retry"
        assert decide_recovery(MAX_RETRIES, "something weird happened") == "give_up"

    def test_no_error_message_follows_fixed_retry_policy(self):
        assert decide_recovery(0) == "retry"
        assert decide_recovery(MAX_RETRIES) == "give_up"


class TestBackoffSeconds:
    def test_first_attempt_backs_off_one_second(self):
        assert backoff_seconds(1) == 1.0

    def test_backoff_doubles_each_attempt(self):
        assert backoff_seconds(2) == 2.0
        assert backoff_seconds(3) == 4.0
        assert backoff_seconds(4) == 8.0

    def test_backoff_is_capped(self):
        assert backoff_seconds(100) == 30.0

    def test_zero_or_negative_attempt_does_not_error(self):
        assert backoff_seconds(0) == 1.0
        assert backoff_seconds(-5) == 1.0
