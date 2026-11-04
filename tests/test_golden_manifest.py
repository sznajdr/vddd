import pytest

from tripstate.golden import Candidate, build_manifest, check_split, diff_heldout, validate_manifest


def pool(n=48):
    out = []
    for i in range(n):
        fmt = ["autostart", "volte_flat", "volte_handicap"][i % 3]
        out.append(Candidate(f"r{i:02d}", "2026-11-01", fmt, ["GP", "PP"][i % 2], ["day", "night"][i % 2],
                             10 + i % 5, boring=(i % 4 == 0), expected_breaks=1 + (i % 2), source_hash=f"h{i}",
                             excluded_from_heldout=(i < 3)))
    return out


def test_build_is_deterministic_and_satisfies_constraints():
    a = build_manifest(pool(), seed=7)
    b = build_manifest(pool(), seed=7)
    assert a["entries"] == b["entries"] and validate_manifest(a) == []
    held = [e for e in a["entries"] if e["split"] == "heldout"]
    assert len(held) == 10 and all(not e["excluded_from_heldout"] for e in held)
    assert sum(e["start_format"] == "volte_handicap" for e in held) >= 2
    assert build_manifest(pool(), seed=8)["entries"] != a["entries"]


def test_build_fails_loudly_when_impossible():
    cands = [Candidate(f"r{i}", "d", "autostart", "GP", "day", 12, False, 0) for i in range(40)]
    with pytest.raises(RuntimeError):
        build_manifest(cands, seed=1, max_attempts=20)


def test_check_split_and_heldout_diff():
    m = build_manifest(pool(), seed=7)
    rows = [{"race_id": e["race_id"], "split": e["split"]} for e in m["entries"][:5]]
    assert check_split(m, rows) == []
    rows[0]["split"] = "heldout" if rows[0]["split"] == "dev" else "dev"
    assert len(check_split(m, rows + [{"race_id": "zzz", "split": "dev"}])) == 2
    m2 = build_manifest(pool(), seed=9, version="1.1", reason="replace corrupt replay")
    d = diff_heldout(m, m2)
    assert d["reason"] == "replace corrupt replay" and (d["added"] or d["removed"])
