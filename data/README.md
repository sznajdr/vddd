# data/ — local layout (gitignored)

```
data/
  raw/<race_id>/replay.<ext>          source replay as pulled (never modified)
  raw/<race_id>/metadata.json         ingest record (see M0 input contract)
  normalized/<race_id>/replay.mp4     M0 output at normalized_fps
  od1x/                               OD-1x recording sheets (copies of protocols/OD-1x/sheets/*.csv, filled)
  pilot5/                             5-race throwaway pilot outputs (producer_kind = pilot_throwaway)
  golden/manifest-vX.Y.yaml           versioned golden manifest (§6.1) — only after freeze
  golden/hand_charts/                 hand charts (OD-3) — only after freeze
  store/tripstate.sqlite              M8 relational store
  store/sidecars/                     parquet frame-level series
```

`race_id` convention: `YYYYMMDD-R<meeting>-C<race>` plus official ID when known, e.g. `20261103-R1-C4`.
