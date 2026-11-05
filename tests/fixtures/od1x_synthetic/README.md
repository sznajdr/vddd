# Synthetic OD-1x sheets + pilot reports — freeze dry-run fixture

**Not evidence.** Every number here is invented so that `tools/promote_draft.py --dry-run` and the
calibration/evaluation dry runs can exercise the D-36 mechanics end to end before OD-1x happens.
The sheets follow `protocols/OD-1x/sheets/*.csv` column for column; `pilot_reports/` carries the five
fields `tools/pilot_report.py` aggregates. `evidence_gated.template.yaml` matches the real registry exactly; the old synthetic policy entry was removed after L-48. `kill_gates_pass.yaml` has KG-1…KG-4 `pass` with synthetic measurements and KG-5
`not_evaluated` to exercise the advisory path.

Regenerate the instantiated registry with:

```bash
python tools/instantiate_eg.py tests/fixtures/od1x_synthetic --registry tests/fixtures/od1x_synthetic/evidence_gated.template.yaml \
  --pilot-reports 'tests/fixtures/od1x_synthetic/pilot_reports/*.json' --out /tmp/eg-synthetic.yaml --date 2026-11-04
```
