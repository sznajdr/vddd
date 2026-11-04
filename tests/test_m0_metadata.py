"""M0 acceptance fixtures (SPEC-2.0.0-draft §4 M0) + S-3/S-5."""
from tripstate.m0_ingest import RaceIn, RunnerIn, normalize_race, normalize_runner_time


def _race(race_id, base, start_type, start_format, runners, piste="GP"):
    return RaceIn(race_id, base, start_type, start_format, tuple(runners), piste)


def test_2100_autostart_direct_elapsed(ts):
    r = _race("A", 2100, "autostart", "autostart", [
        RunnerIn(1, 2100, official_elapsed_s=157.5, official_km_rate_s=75.0, autostart_row=1),
        RunnerIn(2, 2100, official_elapsed_s=158.0, official_km_rate_s=75.2, autostart_row=2),
    ])
    n = normalize_race(r, ts)
    assert not n.ingest_failed
    assert n.runners[0].time_normalization_status == "direct_elapsed"
    assert n.runners[0].official_elapsed_norm_s == 157.5
    assert n.runners[0].rendement_m == 0 and not n.start_handicap


def test_2850_flat_volte(ts):
    r = _race("B", 2850, "volte", "volte_flat", [RunnerIn(1, 2850, official_km_rate_s=76.0)])
    n = normalize_race(r, ts)
    assert not n.ingest_failed
    assert n.runners[0].time_normalization_status == "km_rate_derived"  # S-3 branch
    assert abs(n.runners[0].official_elapsed_norm_s - 76.0 * 2.85) < 1e-9


def test_handicap_winner_at_2900_uses_own_distance(ts):
    r = _race("C", 2850, "volte", "volte_handicap", [
        RunnerIn(1, 2850, official_km_rate_s=77.0),
        RunnerIn(2, 2875, official_km_rate_s=76.5),
        RunnerIn(3, 2900, official_km_rate_s=76.0),  # winner from the back mark
    ])
    n = normalize_race(r, ts)
    assert not n.ingest_failed and n.start_handicap
    w = next(x for x in n.runners if x.saddle_no == 3)
    assert w.rendement_m == 50
    assert abs(w.official_elapsed_norm_s - 76.0 * 2.9) < 1e-9


def test_elapsed_duplicates_km_rate(ts):
    s, norm, codes = normalize_runner_time(76.0, 76.0, 2850, ts)
    assert s == "km_rate_derived" and codes == ["elapsed_is_km_rate"]
    assert abs(norm - 76.0 * 2.85) < 1e-9


def test_disagreeing_fields(ts):
    s, norm, codes = normalize_runner_time(200.0, 76.0, 2850, ts)
    assert s == "unavailable" and norm is None and codes == ["time_fields_disagree"]



def test_malformed_row_242_vs_120(ts):
    s, norm, codes = normalize_runner_time(242.0, 120.0, 2100, ts)
    assert s == "unavailable" and norm is None and codes == ["time_fields_disagree"]


def test_winner_with_no_time_no_code(ts):
    s, norm, codes = normalize_runner_time(None, None, 2100, ts)
    assert s == "unavailable" and norm is None and codes == []


def test_s3_elapsed_only_plausible_is_direct(ts):
    s, norm, _ = normalize_runner_time(157.5, None, 2100, ts)
    assert s == "direct_elapsed" and norm == 157.5


def test_s3_elapsed_only_implausible(ts):
    s, _, codes = normalize_runner_time(100.0, None, 2100, ts)  # 47.6 s/km
    assert s == "unavailable" and codes == ["elapsed_implausible"]


def test_s5_km_rate_60_is_now_implausible(ts):
    s, _, codes = normalize_runner_time(None, 60.0, 2100, ts)
    assert s == "unavailable" and codes == ["km_rate_implausible"]


def test_start_format_invariants_fail_ingest(ts):
    r = _race("D", 2100, "autostart", "volte_flat", [RunnerIn(1, 2100)])
    assert normalize_race(r, ts).ingest_failed
    r = _race("E", 2850, "volte", "volte_flat", [RunnerIn(1, 2875)])
    assert "rendement_in_non_handicap" in normalize_race(r, ts).failure_reasons
    r = _race("F", 2850, "volte", "volte_handicap", [RunnerIn(1, 2850)])
    assert "handicap_without_rendement" in normalize_race(r, ts).failure_reasons


def test_distance_below_base_fails_never_inferred(ts):
    r = _race("G", 2850, "volte", "volte_flat", [RunnerIn(1, None), RunnerIn(2, 2800)])
    n = normalize_race(r, ts)
    assert n.ingest_failed and len(n.runners) == 0


def test_rendement_not_25m_is_soft(ts):
    r = _race("H", 2850, "volte", "volte_handicap", [RunnerIn(1, 2850), RunnerIn(2, 2860)])
    n = normalize_race(r, ts)
    assert not n.ingest_failed and n.metadata_conflict_codes == ["rendement_not_25m"]


def test_piste_and_autostart_row_domains(ts):
    r = _race("I", 2100, "autostart", "autostart", [RunnerIn(1, 2100, autostart_row=3)])
    assert any(x.startswith("autostart_row_invalid") for x in normalize_race(r, ts).failure_reasons)
    assert normalize_race(_race("J", 2100, "autostart", "autostart", [RunnerIn(1, 2100)], piste=None), ts).piste is None
