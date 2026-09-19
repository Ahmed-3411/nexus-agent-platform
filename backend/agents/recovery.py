"""
Recovery policy for failed steps.

Phase 2 retried every failure up to a fixed count. Phase 4 adds two
things the original brief called for:

  1. Distinguishing transient errors (timeouts, connection issues, rate
     limits — worth retrying) from permanent ones (a table that doesn't
     exist, a policy rejection, invalid arguments — retrying is pointless
     and just burns attempts/latency/cost for a guaranteed-identical
     failure). A permanent error gives up immediately regardless of how
     many retries are left.
  2. Exponential backoff: `backoff_seconds()` tells the caller how long
     to wait before the next attempt, so a transient failure (e.g. a
     database blip) gets a real chance to clear before retrying, instead
     of hammering the same failing call back-to-back.

Attempt history persistence into `workflow_steps.attempt_count` is left
for when the API layer is wired to the database.
"""
from typing import Literal

MAX_RETRIES = 2
MAX_BACKOFF_SECONDS = 30.0

# Keyword fragments (matched case-insensitively) that indicate the error
# is almost certainly transient and safe to retry as-is.
_TRANSIENT_KEYWORDS = (
    "timeout",
    "timed out",
    "connection",
    "temporarily unavailable",
    "rate limit",
    "unavailable",
    "reset by peer",
    "try again",
)

# Keyword fragments that indicate the error will happen again no matter
# how many times we retry — a schema/permissions/validation problem, not
# a flaky network blip.
_PERMANENT_KEYWORDS = (
    "does not exist",
    "not permitted",
    "forbidden",
    "denied",
    "invalid",
    "not found",
    "notreadonly",
    "only select",
    "unauthorized",
    "not configured",
    "credentials are not configured",
    "requires a valid read-only",
    "accepts only read-only",
)

ErrorClass = Literal["transient", "permanent", "unknown"]


def classify_error(error: str | None) -> ErrorClass:
    if not error:
        return "unknown"
    lowered = error.lower()
    if any(keyword in lowered for keyword in _PERMANENT_KEYWORDS):
        return "permanent"
    if any(keyword in lowered for keyword in _TRANSIENT_KEYWORDS):
        return "transient"
    return "unknown"


def decide_recovery(attempt_count: int, error: str | None = None) -> Literal["retry", "give_up"]:
    """
    Return "retry" if another attempt should be made, else "give_up".

    A permanent error gives up immediately, even on the very first
    attempt — there is no point burning retries on a guaranteed failure.
    Transient and unknown errors follow the fixed-retry-count policy.
    """
    if classify_error(error) == "permanent":
        return "give_up"
    if attempt_count < MAX_RETRIES:
        return "retry"
    return "give_up"


def backoff_seconds(attempt_count: int) -> float:
    """
    Exponential backoff, capped at MAX_BACKOFF_SECONDS: 1s, 2s, 4s, 8s...

    `attempt_count` is the attempt number about to be made (1-indexed);
    callers are not required to actually sleep this long (Phase 4 only
    computes the value — an execution layer that awaits it belongs to
    whatever eventually schedules real retries against live MCP servers).
    """
    return min(2.0**max(attempt_count - 1, 0), MAX_BACKOFF_SECONDS)
