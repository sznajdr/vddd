"""Version constants. `schema_version` equals the governing SPEC semver (§9 invariants)."""

SPEC_VERSION = "2.0.0-draft"
SCHEMA_VERSION = SPEC_VERSION
SPEC_STATUS = "DRAFT"  # becomes FROZEN only via the D-36 promotion commit


def is_frozen() -> bool:
    return SPEC_STATUS == "FROZEN"
