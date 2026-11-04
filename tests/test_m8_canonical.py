import math

import pytest

from tripstate.m8_storage import canonical_jsonl, canonical_sha256, ordinal_ids, quantize


def test_quantize_fixed_decimals():
    assert quantize(0.1 + 0.2, 4) == "0.3000"
    assert quantize(1.23456789, 6) == "1.234568"
    assert quantize(-0.00001, 3) == "0.000"
    with pytest.raises(ValueError):
        quantize(math.nan, 3)


def test_canonical_is_stable_across_float_noise_and_order():
    order = ["race_id", "saddle_no", "seg_id", "t_start_frac", "l_sl", "created_at", "metadata_conflict_codes"]
    pk = ["race_id", "saddle_no", "seg_id"]
    a = [
        {"race_id": "r", "saddle_no": 2, "seg_id": 0, "t_start_frac": 0.1 + 0.2, "l_sl": 1.00004, "created_at": "x", "metadata_conflict_codes": ["b", "a"]},
        {"race_id": "r", "saddle_no": 1, "seg_id": 0, "t_start_frac": 0.5, "l_sl": 2.0, "created_at": "y", "metadata_conflict_codes": []},
    ]
    b = [dict(a[1], created_at="z"), dict(a[0], t_start_frac=0.3, l_sl=1.00004000001)]
    ja, jb = canonical_jsonl(a, order, pk), canonical_jsonl(b, order, pk)
    assert ja == jb and canonical_sha256(ja) == canonical_sha256(jb)
    assert "created_at" not in ja and ja.endswith("\n") and "\r" not in ja
    assert '"metadata_conflict_codes":["a","b"]' in ja


def test_rejects_unknown_columns_and_nan():
    with pytest.raises(ValueError):
        canonical_jsonl([{"race_id": "r", "zzz": 1}], ["race_id"], ["race_id"])
    with pytest.raises(ValueError):
        canonical_jsonl([{"race_id": "r", "x_sl": math.inf}], ["race_id", "x_sl"], ["race_id"])


def test_ordinal_ids_deterministic():
    recs = [{"t_start_frac": 0.5, "state": "B"}, {"t_start_frac": 0.1, "state": "A"}, {"t_start_frac": 0.5, "state": "A"}]
    out = ordinal_ids(recs, "seg_id", "t_start_frac")
    assert [r["seg_id"] for r in out] == [0, 1, 2]
    assert [r["state"] for r in out] == ["A", "A", "B"]
    assert ordinal_ids(list(reversed(recs)), "seg_id", "t_start_frac") == out
