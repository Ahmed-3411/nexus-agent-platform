"""
Default role -> permission grants.

This mirrors the `role_permissions` seed data in backend/db/schema.sql
exactly. It exists so the Policy Engine can be used and unit-tested
without a database connection; `policies/loader.py` provides the DB-backed
equivalent for when the API is wired up to real, editable role grants.

If you change the seed data in schema.sql, update this dict too — a unit
test (tests/unit/test_policy_engine.py) checks the two agree on the
default set of roles.
"""

DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "database.read",
        "database.write",
        "database.delete",
        "email.read",
        "email.draft",
        "email.send",
        "files.read",
        "crm.read",
        "crm.update",
    },
    "manager": {
        "database.read",
        "email.read",
        "email.draft",
        "email.send",
        "files.read",
        "crm.read",
        "crm.update",
    },
    "analyst": {
        "database.read",
        "email.read",
        "files.read",
        "crm.read",
    },
    "support_agent": {
        "email.read",
        "email.draft",
        "files.read",
        "crm.read",
        "crm.update",
    },
}
