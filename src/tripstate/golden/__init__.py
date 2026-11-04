"""Golden fixture manifest (§6.1; S-6). Build only after the 2.0.0 freeze; the tool is ready now."""
from tripstate.golden.manifest import (
    Candidate,
    build_manifest,
    check_split,
    diff_heldout,
    validate_manifest,
)

__all__ = ["Candidate", "build_manifest", "check_split", "diff_heldout", "validate_manifest"]
