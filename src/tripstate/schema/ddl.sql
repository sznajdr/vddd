-- SPEC-2.0.0-draft §9 — relational schema (SQLite dialect). Abridged keys per spec; every
-- versioned artifact key includes producer_version; CV uniqueness adds extractor_version +
-- threshold_set_version. Frame-level series live in parquet sidecars (geometry, tracklets).
-- schema_version == SPEC semver. created_at is operational: stored, excluded from canonical export.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS versions (
  producer_version TEXT PRIMARY KEY,
  producer_kind TEXT NOT NULL CHECK (producer_kind IN ('cv_extract','human_chart','text_parse','config','pilot_throwaway')),
  extractor_version TEXT,
  module_git_hashes TEXT, model_weight_hashes TEXT,
  determinism_env TEXT,          -- D-32: use_deterministic_algorithms, cudnn.benchmark, TF32, driver
  schema_version TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS threshold_sets (
  threshold_set_version TEXT PRIMARY KEY,
  registry_yaml TEXT NOT NULL, search_provenance TEXT,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS races (
  race_id TEXT PRIMARY KEY,
  date TEXT NOT NULL, meeting TEXT NOT NULL, race_no INTEGER NOT NULL, official_id TEXT,
  base_distance_m INTEGER NOT NULL,
  start_type TEXT NOT NULL CHECK (start_type IN ('volte','autostart')),
  start_format TEXT NOT NULL CHECK (start_format IN ('autostart','volte_flat','volte_handicap')),
  start_handicap INTEGER NOT NULL,
  piste TEXT CHECK (piste IN ('GP','PP')),                       -- DR-06, from ingest only
  arrival_revised INTEGER,                                        -- NULL allowed; never defaulted (D-25)
  metadata_conflict_codes TEXT NOT NULL DEFAULT '[]',             -- lex-sorted JSON array
  source_uri TEXT, source_hash TEXT, normalized_hash TEXT,
  fps REAL, width INTEGER, height INTEGER, duration_s REAL,
  ingest_failed INTEGER NOT NULL DEFAULT 0, failure_reasons TEXT,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runners (
  race_id TEXT NOT NULL REFERENCES races(race_id), saddle_no INTEGER NOT NULL,
  driver TEXT, horse TEXT, post_or_band TEXT,
  autostart_row INTEGER CHECK (autostart_row IN (1,2)),           -- DR-04
  distance_run_m INTEGER NOT NULL, rendement_m INTEGER NOT NULL,
  finish_position INTEGER, provisional_position INTEGER,
  official_status TEXT,
  arrival_revision_type TEXT CHECK (arrival_revision_type IN ('none','retrograde','post_finish_dq','other','unknown')),
  official_elapsed_s REAL, official_km_rate_s REAL,
  raw_elapsed_str TEXT, raw_km_rate_str TEXT,
  time_normalization_status TEXT NOT NULL CHECK (time_normalization_status IN ('direct_elapsed','km_rate_derived','unavailable')),
  official_elapsed_norm_s REAL,
  conflict_codes TEXT NOT NULL DEFAULT '[]',
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, saddle_no)
);

CREATE TABLE IF NOT EXISTS shots (
  race_id TEXT NOT NULL REFERENCES races(race_id), shot_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('wide_pan','head_on','tight','replay_insert','graphic_fullscreen','other')),
  t_start_video_s REAL NOT NULL, t_end_video_s REAL NOT NULL, confidence REAL NOT NULL,
  graphic_overlay_mask_ref TEXT,
  extractor_version TEXT NOT NULL, threshold_set_version TEXT NOT NULL,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, shot_id, producer_version)
);

CREATE TABLE IF NOT EXISTS tracklets (
  race_id TEXT NOT NULL, shot_id INTEGER NOT NULL, tracklet_id INTEGER NOT NULL,
  boxes_sidecar_sha256 TEXT NOT NULL, tracker_params_hash TEXT NOT NULL,
  extractor_version TEXT NOT NULL, threshold_set_version TEXT NOT NULL,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, shot_id, tracklet_id, producer_version)
);

CREATE TABLE IF NOT EXISTS id_assignments (
  race_id TEXT NOT NULL, shot_id INTEGER NOT NULL, tracklet_id INTEGER NOT NULL,
  saddle_no INTEGER NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('human_seed','propagation','human_correction')),
  human_confirmed INTEGER NOT NULL, seed_frame INTEGER, seed_video_s REAL,
  extractor_version TEXT NOT NULL, threshold_set_version TEXT NOT NULL,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, shot_id, tracklet_id, producer_version)
);

CREATE TABLE IF NOT EXISTS race_anchors (
  race_id TEXT NOT NULL REFERENCES races(race_id),
  t0_frame INTEGER, t0_video_s REAL, t0_method TEXT,
  tend_frame INTEGER, tend_video_s REAL, tend_method TEXT,
  first_past_saddle_no INTEGER,
  first_past_method TEXT CHECK (first_past_method IN ('official_unrevised','official_assumed','observed_crossing','human_confirm')),
  finish_evidence_n INTEGER,                                      -- D-30: observed crossings backing rung (ii)
  official_time_method TEXT NOT NULL CHECK (official_time_method IN ('direct_elapsed','km_rate_derived','unavailable')),
  anchor_check_status TEXT NOT NULL CHECK (anchor_check_status IN ('pass','mismatch','inconclusive')),
  anchor_duration_delta_s REAL, anchor_suspect INTEGER NOT NULL, human_confirmed INTEGER NOT NULL,
  recall_suspected INTEGER NOT NULL DEFAULT 0,                    -- EC-14
  extractor_version TEXT, threshold_set_version TEXT,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, producer_version)
);

CREATE TABLE IF NOT EXISTS shot_calibrations (
  race_id TEXT NOT NULL, shot_id INTEGER NOT NULL,
  travel_direction_sign INTEGER NOT NULL CHECK (travel_direction_sign IN (-1,1)),
  rail_side TEXT NOT NULL CHECK (rail_side IN ('left_of_travel','right_of_travel')),
  travel_conf REAL, rail_conf REAL,
  sw_ratio_method TEXT,                                           -- RP-5 placeholder; NULL = global sw_ratio
  method TEXT NOT NULL CHECK (method IN ('heuristic','human_confirm')), human_confirmed INTEGER NOT NULL,
  extractor_version TEXT NOT NULL, threshold_set_version TEXT NOT NULL,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, shot_id, producer_version)
);

-- Shared segment payload (D-05): state_segments (CV) and hand_charts (human/text).
CREATE TABLE IF NOT EXISTS state_segments (
  race_id TEXT NOT NULL, saddle_no INTEGER NOT NULL, seg_id INTEGER NOT NULL,
  state_kind TEXT NOT NULL CHECK (state_kind IN ('base','overlay')),
  state TEXT NOT NULL,
  covered INTEGER,
  lead_uncovered_outside INTEGER,                                 -- L-37 (was first_over)
  lead_uncovered_outside_ambiguous INTEGER,
  tier_attr INTEGER, end_attr TEXT CHECK (end_attr IN ('front','rear')),
  method TEXT NOT NULL CHECK (method IN ('cv_extract','human_chart','text_parse')),
  t_start_frac REAL NOT NULL, t_end_frac REAL NOT NULL, confidence REAL,
  visibility TEXT NOT NULL CHECK (visibility IN ('visible','not_visible','unknown')),
  start_truncated INTEGER NOT NULL, end_truncated INTEGER NOT NULL,
  extractor_version TEXT NOT NULL, threshold_set_version TEXT NOT NULL,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, saddle_no, seg_id, producer_version, extractor_version, threshold_set_version)
);

CREATE TABLE IF NOT EXISTS hand_charts (
  race_id TEXT NOT NULL, saddle_no INTEGER NOT NULL, seg_id INTEGER NOT NULL,
  state_kind TEXT NOT NULL, state TEXT NOT NULL, covered INTEGER,
  lead_uncovered_outside INTEGER, lead_uncovered_outside_ambiguous INTEGER,
  tier_attr INTEGER, end_attr TEXT,
  method TEXT NOT NULL CHECK (method IN ('human_chart','text_parse')),
  t_start_frac REAL, t_end_frac REAL, confidence REAL,
  visibility TEXT NOT NULL, start_truncated INTEGER NOT NULL, end_truncated INTEGER NOT NULL,
  charter_minutes REAL,
  split TEXT NOT NULL CHECK (split IN ('dev','heldout')),         -- denormalized copy of the manifest (S-6)
  phase TEXT, source_text_id TEXT, source_phrase TEXT, mapping_rule_version TEXT,
  mapping_confidence REAL, mapping_status TEXT, candidate_states TEXT,  -- §11.3 (text_parse only)
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, saddle_no, seg_id, producer_version)
);

CREATE TABLE IF NOT EXISTS events (
  race_id TEXT NOT NULL, saddle_no INTEGER, event_id INTEGER NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('BREAK','SHOT_GAP')),
  t_start_frac REAL NOT NULL, t_end_frac REAL,
  positions_lost INTEGER, positions_lost_basis_n INTEGER,         -- L-15 (F-7)
  recovered INTEGER,
  source_shot_types TEXT, shot_type_before TEXT, shot_type_after TEXT,
  method TEXT NOT NULL CHECK (method IN ('cv_extract','human_chart','text_parse')),
  review_status TEXT NOT NULL CHECK (review_status IN ('pending','accepted','rejected')),
  human_confirmed INTEGER NOT NULL, reviewed_at TEXT,
  dai_tag TEXT CHECK (dai_tag IN ('dai_uncaught_break_expected','dai_gait_other')),  -- L-26
  extractor_version TEXT, threshold_set_version TEXT,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, saddle_no, event_id, producer_version)
);

CREATE TABLE IF NOT EXISTS qc (
  race_id TEXT NOT NULL REFERENCES races(race_id),
  chartable INTEGER NOT NULL, failure_codes TEXT NOT NULL DEFAULT '[]',
  coverage_race REAL, coverage_final_third REAL, human_minutes REAL,
  stratum TEXT CHECK (stratum IN ('day','night')),
  finish_check_status TEXT, finish_check_basis TEXT, start_check_status TEXT, anchor_check_status TEXT,
  id_suspect INTEGER NOT NULL, anchor_suspect INTEGER NOT NULL,
  pct_graphic_occluded REAL, pct_pack_coherent REAL, pct_rail_reference_valid REAL,
  n_truncated_segments INTEGER, n_replay_inserts INTEGER,
  realization TEXT,                                               -- DR-11 coverage-failure tag
  recall_suspected INTEGER NOT NULL DEFAULT 0,                    -- EC-14
  extractor_version TEXT, threshold_set_version TEXT,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, producer_version)
);

CREATE TABLE IF NOT EXISTS runner_qc (
  race_id TEXT NOT NULL, saddle_no INTEGER NOT NULL,
  pct_time_visible REAL, pct_final_third_visible REAL,
  pct_time_stateable REAL, pct_final_third_stateable REAL,
  occl_events INTEGER, denom_start_frac REAL, denom_end_frac REAL,
  terminal_reason TEXT, terminal_frac REAL, terminal_before_final_third INTEGER,
  extractor_version TEXT, threshold_set_version TEXT,
  schema_version TEXT NOT NULL, producer_version TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (race_id, saddle_no, producer_version)
);

-- Default feature-export view (D-11): chartable only; no override parameter exists at this layer.
CREATE VIEW IF NOT EXISTS v_state_segments_chartable AS
  SELECT s.* FROM state_segments s JOIN qc q
    ON q.race_id = s.race_id AND q.producer_version = s.producer_version
  WHERE q.chartable = 1;
