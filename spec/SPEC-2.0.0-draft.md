# SPEC-2.0.0-draft — Vincennes Attelé Trip-State Extraction Pipeline

**Status:** DRAFT (D-36). Not normative for golden charting or calibration. Agents MAY build M0, schema migrations and tooling scaffolds against it; golden charting (OD-3), calibration (§7) and M2 training MUST NOT begin. Every value marked `[EG: …]` is provisional until `registers/evidence_gated.yaml` instantiates it.
**Promotion rule (D-36):** this file becomes `SPEC-2.0.0.md`, Status FROZEN, in one commit when (1) every `[EG]` entry is instantiated, (2) every kill-gate in §0.4 passes, (3) D-26…D-36 are appended to §1, (4) `tools/freeze_check.py` exits 0.
**Version:** 2.0.0-draft — diff base SPEC-1.2.0 (last FROZEN 1.x); edit ledger `SPEC-2.0.0-draft-LEDGER.md`; cut by `tools/cut_draft.py`. MAJOR because D-17 is reopened (headline re-cut, D-27), a D-08-frozen core definition changes (cover, D-26) and a payload field is renamed (`first_over` → `lead_uncovered_outside`).
**Audience:** Coding agents building modules against this spec; project owner auditing decisions.
**Language:** The key words MUST, MUST NOT, SHALL, SHOULD, SHOULD NOT, MAY are to be interpreted as in RFC 2119. Anything not marked normative is informative.
**Prime directive:** When uncertain, **FLAG AND DEGRADE, NEVER GUESS.** Every module MUST prefer `LOW_CONF`, `UNKNOWN`, `NOT_VISIBLE` or race-level `unchartable` over fabricating a value. This mirrors the explicit-only extraction principle used elsewhere in the owner's tooling.

---

## 0. Purpose & Success Criteria

### 0.1 Purpose (informative)

Extract per-horse **trip-state charts** from Equidia broadcast replays of Vincennes trot attelé races. The output is a structured, versioned record of topological race states (cover, width tier, position rank, breaks) that are (a) invisible in commercially available French trot data, (b) known from handicapping literature to carry predictive information, and (c) intended as overlay features for a downstream prediction model. The downstream model is **out of scope** for this spec (§12).

The stable artifact is the **trip-state segment payload** (§2/§9). The CV pipeline is one implementation that fills it; human hand-charting uses the same payload, and future text parsing uses its schema-additive phase-granularity extension (§11).

### 0.2 v1 Definition of Done (normative)

The pipeline is v1-complete when ALL of the following hold:

| ID | Criterion |
|----|-----------|
| DoD-1 | On the held-out golden set (§6), both the **uncovered-outside mask IoU** (`tier ≥ 2 ∧ covered = false`, §6.2) and the **covered-mask IoU** (`covered = true`, §6.2–6.3) are **≥ 0.85**. The `PARKED` label is no longer a floor (D-27). |
| DoD-2 | On the same held-out golden set, pre-review break-candidate recall vs. hand charts has a **point estimate ≥ 0.80**, reported with its Wilson 95% confidence interval — at the §6.1 fixture size this is a point estimate, not a certification (D-31); final `BREAK` events require human acceptance. There is no separate precision floor in v1, but candidate load remains constrained by M6. |
| DoD-3 | Median human time per eligible race attempt (seeding + re-seeds + anchors + break confirmation), including attempts later excluded as `over_budget`, is **≤ 5 minutes** `[EG: pilot → dod3_median_target_min]`, measured over ≥ 20 consecutive eligible attempts. The operational cap is Q-7's `human_budget_cap_min`, not this target (D-29). |
| DoD-4 | QC gates (§10) are enforced in code; no state segment or aggregate from a race flagged `unchartable` appears in default feature/export views. Raw diagnostic artifacts MAY persist behind the explicit override in M7. |
| DoD-5 | Every CV-pipeline output row carries non-null `extractor_version` and `threshold_set_version`; every artifact carries `schema_version` and `producer_version`. Re-running the pipeline on the same inputs reproduces an identical **quantized canonical** data payload (§9, D-32), excluding operational timestamps. |
| DoD-6 | At least **8 of the 10** held-out races pass Q-1 through Q-6 and therefore remain eligible for state/break accuracy evaluation. Accuracy floors cannot be met by abstaining on most held-out races. |

Threshold **values** in DoD-1/2 MAY be revised via the calibration procedure (§7) with a version bump; the **structure** of the criteria MUST NOT change within v1.

For DoD-5, "same inputs" includes the same persisted human artifacts (identity assignments, rail confirmations, timeline anchors, arrival-revision adjudications and break review decisions). It does not mean asking the operator to repeat those actions; operator wall-clock logs are operational metadata.

### 0.3 Dependency register (normative)

| ID | Dependency | Blocks | Owner |
|----|-----------|--------|-------|
| OD-1x | Timed dry run on 3 sample replays (one autostart, one flat volte, one handicap volte, D-22; pistes per DR-06) per `protocols/OD-1x/PROTOCOL.md`: timed seeding, anchor reproducibility and bias per start type, wide-pan coverage, geometry eyeball incl. lateral scale, finish-shot crossing evidence, recall scan. Supersedes OD-1. | Instantiating every `[EG]` value (§7.1, `registers/evidence_gated.yaml`); freezing M1 shot-type classes; golden fixture selection (§6.1); the 2.0.0 freeze (D-36). | Project owner |
| OD-2 | **RESOLVED (2026-07-25):** owner's NLP vocabulary integrated into §11 with corpus/parser provenance and ambiguity guards. | — | Project owner |
| OD-3 | Golden annotation pack: 30 dev + 10 held-out hand charts plus the M2/M4 frame fixtures defined in §6.1. | M2/M4 acceptance; calibration (§7); DoD-1/2/6 evaluation. | Project owner |
| OD-4 | Authoritative arrival-revision/incident field identified in the Equidia ingest and scraped into `arrival_revised` / `arrival_revision_type`. Until resolved, first-past resolution runs in `official_assumed` mode (D-25) and `arrival_revised` remains NULL. | Upgrade of `official_assumed` → `official_unrevised`; nothing else — the pipeline is fully functional without it. | Project owner |

Until OD-1x resolves, all camera/shot assumptions in this spec are **provisional-normative**: agents MUST build against them but MUST NOT hard-code them beyond the config layer.

### 0.4 Kill-gates (normative structure; values `[EG]`; D-33)

The project defines when to stop, not only when it is done. Evaluated after OD-1x and a 5-race pilot; machine copy in `registers/kill_gates.yaml`.

| ID | Gate | On trigger |
|----|------|------------|
| KG-1 | Median seeding time (first stable wide-pan frame → all saddle numbers assigned) > 8 min `[EG]` | Stop; reconsider CV against pure hand-charting / text-parse |
| KG-2 | M4 tier agreement < 0.85 on pilot hand-labelled frames | Recalibrate once; still failing → stop |
| KG-3 | Pilot `chartable` yield < 40 % | Gate review before any further charting |
| KG-4 | Post-offset anchor residual spread > 2 × provisional tolerance on either start type | EC-12 design review before freeze |

**Pilot exemption (normative).** The 5-race pilot runs on a throwaway stack that is exempt from gates G-1…G-3 (§4.0). Its outputs carry `producer_kind = pilot_throwaway`, are evidence for the freeze only, and MUST NOT enter the corpus, the golden set or calibration. The pilot's 5 races and the 3 OD-1x replays MAY later be dev races but MUST NOT be held-out races.

---

## 1. Decision Log (normative — closed decisions)

Agents MUST NOT re-litigate closed decisions. Proposals that conflict with an entry below MUST be rejected with a pointer to the entry. Reopening a decision requires a spec version bump authorized by the project owner.

| ID | Decision | Rationale (one line) |
|----|----------|----------------------|
| D-01 | Identity assignment is **semi-automatic (human-in-the-loop seeding)**. Post-hoc anchoring (finish order + post positions) is used as a consistency check only. Fully automatic OCR/silk re-ID is **banned in v1**. | Weeks-to-working beats months-to-maybe; seeding clicks double as future re-ID training data. |
| D-02 | v1 tracks **one shot type only: the main wide pan**. All other shots are discarded from state extraction. The chosen shot type MAY be revised after OD-1 inspection if another single shot proves more informative; cross-shot stitching remains banned (§12). | One shot = one geometry assumption; stitching is a research project. |
| D-03 | v1 state set: cover status, width tier, position rank, break detection (recovered breaks). Stretch-block deferred to v1.5. Whip, head carriage, driver gaze, fatigue: **banned in v1** (§12). | Topological states survive broadcast footage; metric/pose states do not. |
| D-04 | States are computed per frame, stored as **segments** carrying `(horse, state_kind, state, covered, attributes, t_start_frac, t_end_frac, confidence, visibility)`. Temporal anchoring is fraction-of-race-elapsed, not track landmarks. | Panning broadcast has no reliable landmarks; segments compress without losing events. |
| D-05 | Ground truth = owner hand charts using the schema in §2. Extractor accuracy is evaluated against hand charts **before** any predictive-value work. | An extractor that can't reproduce a human chart is noise, not signal. |
| D-06 | v1 corpus: **Vincennes, attelé only, field size ≤ 14**. Monté excluded (separate gait dynamics → separate spec). | Volume + consistent production + owner's betting focus; big fields are occlusion hell. |
| D-07 | Runner geometry lives in **pack-relative coordinates** (§3): longitudinal/lateral projection onto the pack's principal axis, distances in median-bbox "sulky lengths". The detected rail reference is the sole shot-relative anchor and is used only to decide whether occupied cluster 1 is absolute tier 1. Pixel-space thresholds are banned. | Pack-space is zoom/pan-invariant; a rail anchor prevents empty-lane renumbering without pretending pixels are meters. |
| D-08 | State/event definitions of §2.3–2.5 are structurally frozen; numeric thresholds are **config, not constants** (§7). | Structure is the schema; numbers are calibration. |
| D-09 | A shot segmenter gates the tracker to wide-pan segments. Human budget **≤ 5 min/race**; races exceeding it are flagged `over_budget`, set `chartable = false` and skipped, never heroically rescued. | Budget discipline keeps the corpus honest and the owner sane. |
| D-10 | Timeline anchors: `t_0` (start release) and `t_end` (winner crosses finish) are **one human click each**. Official race duration is a sanity check. "Late race" := final 25–30% elapsed (config). | Only anchoring that survives a panning broadcast. |
| D-11 | Coverage is first-class. Races failing coverage gates (§10) are `unchartable`: excluded from feature output, logged, no partial credit. | 600 honest races beat 900 with silent artifacts. |
| D-12 | Before the spec is declared production-real, 3 sample replays MUST be inspected (OD-1). | Every camera assumption here is falsifiable against them. |
| D-13 | Output schema of §9 is frozen in shape; `schema_version` and `producer_version` on every artifact, with non-null `extractor_version` + `threshold_set_version` on every CV-produced row. | Reproducibility and re-run comparability, same as owner's model-versioning discipline. |
| D-14 | Spec register: agents-first, RFC-2119 normative language, decision log, rationale kept to one line per decision (extended rationale only in Annex A). | Terse and unambiguous beats explanatory. |
| D-15 | Normative = I/O contracts + acceptance tests. Tooling = pinned **non-normative** default stack (§13), replaceable if contracts/tests still pass. | Spec survives tooling churn; agents still get a golden path. |
| D-16 | Build order M0→M8 with gates (§4.0). The seeding tool is a first-class module but **minimal**: keyboard-driven CLI/OpenCV-window grade. No web apps in v1. | Tool UX decides whether the 5-min budget holds; effort stays minimal. |
| D-17 | Golden fixtures + quantified acceptance (§6). `PARKED` IoU and covered-mask IoU are weighted highest — parked-without-cover is the money state. | Accuracy targets must be numbers, not vibes. |
| D-18 | Thresholds ship as a **versioned threshold-set** with a calibration procedure (§7). Hard-coding placeholder numbers as physics is banned. | Placeholders are placeholders. |
| D-19 | Edge-case registry (§8) is a living, numbered section designed for owner extension. | The ugly stuff must be enumerated where it can grow. |
| D-20 | Lexicon bridge (§11) has a fixed table shape and evidence/ambiguity rules; owner vocabulary is integrated under OD-2. | One shared semantic bridge prevents text and CV labels from drifting. |
| D-21 | Single markdown file, semver, changelog, explicit out-of-scope register with re-entry versions (§12). | Agent-native, diffable, feeds prompt pipelines. |
| D-22 | Per-runner start distance is first-class metadata: `distance_run_m` / `rendement_m` on every runner, `start_format` on every race. Geometric states and overlays are NEVER corrected or suppressed for start handicaps; structurally induced patterns (e.g. rear `DETACHED` at `t_0` in `volte_handicap`) are conditioned on this metadata downstream. | The chart records what happened; metadata explains why. |
| D-23 | `t_end` anchors on the **first past the post**; D-10's "winner" means that runner regardless of subsequent relegation/DQ. Consistency checks compare observed crossings against crossing-order evidence with a revision carve-out, never raw post-enquête order. | The video timeline is geometric; stewards' decisions are not. |
| D-24 | Official race time is normalized to total elapsed seconds with explicit unit provenance (`official_time_method`); RK derivation uses the first-past runner's actual `distance_run_m`. Unit guessing is fabrication under the prime directive. | RK is a rate, not a duration. |
| D-25 | First-past resolution ladder: directly observed crossing > official winner corroborated by the mandatory crossing reconstruction (`official_assumed`) > human adjudication. `arrival_revised = false` requires an authoritative source or adjudication and MUST NOT be a default; absence of a revision field is not evidence of no revision. | The cheapest honest corroborator is a check M3 already runs. |

**Pending at freeze (D-36):** D-26…D-36 are defined in `decisions/DECISION-LOG.md` and are the agreed direction of this draft; the promotion commit appends them to this table verbatim. They MAY be built against; they MUST NOT be reopened by agents.

---

## 2. Definitions & State Taxonomy (normative)

### 2.1 Entities

| Term | Definition |
|------|-----------|
| **Race** | One officially run Vincennes attelé event, identified by `race_id` (date + meeting + race number, plus official ID when available). |
| **Runner** | A declared starter, identified by saddle-cloth number `saddle_no` within a race. |
| **Tracklet** | A contiguous sequence of detections with a tracker-assigned ID within one wide-pan segment. |
| **Chart** | The complete set of state segments + events + QC record for one race under one `producer_version`; CV charts additionally bind one `extractor_version` and `threshold_set_version`. |
| **Sulky length (SL)** | Median long-side length of all `horse_sulky` bboxes in the current frame. Unit of longitudinal distance. |
| **Sulky width (SW)** | `SL × sw_ratio` (config, default 0.35) — lateral unit derived from SL, since broadcast yaw makes direct width unreliable. |
| **Pack** | The set of tracked runners visible in the current frame with valid pack-space projection. |

### 2.2 Tiers and ordering (computed per frame, in pack-space per §3)

- **Longitudinal rank**: global ordering by descending `l_sl` (1 = furthest advanced; smaller numeric rank = further advanced), with `saddle_no` as a deterministic storage tiebreak. Adjacent runners separated by < `rank_tie_sl` are `order_ambiguous`, so the tiebreak MUST NOT be treated as geometric evidence. M5 emits `UNKNOWN` when the tie would change a base state; when it affects only which PARKED runner is `lead_uncovered_outside`, both retain `PARKED` and use the nullable ambiguity rule in §2.3.
- **Lateral tier**: detect the inner rail boundary at `rail_ref_w_sw`; because increasing `w_sw` points away from the rail, the expected tier-1 runner center is `rail_ref_w_sw + rail_lane_center_offset_sw`. Sort valid runners rail-outward by `(w_sw, saddle_no)`, where `saddle_no` is only a deterministic exact-coordinate tiebreak. Form occupied clusters deterministically: the first runner starts cluster 1; assign each next runner to the current cluster iff its distance from that cluster's current median `w_sw` is < `same_tier_sw`, otherwise start the next cluster; recompute the median after each assignment. Assign occupied cluster 1 to absolute tier 1 only when rail-reference confidence is valid and its center is ≤ `rail_attach_sw` from the expected tier-1 center; otherwise absolute tiers are unresolved and affected runners become `UNKNOWN`. The innermost **occupied** cluster MUST NOT be silently relabeled tier 1 when the rail lane is empty. The strict clustering `<` boundary, closed attachment boundary and median-linkage algorithm are normative. After clustering, any occupied cluster whose lateral span (max − min `w_sw`) exceeds `max_tier_span_sw` (default 1.2 SW `[EG: OD-1x]`) splits recursively at its largest internal gap (ties → the lower-index gap); the bound and the split rule are normative and a unit test with 14 evenly spread runners is part of M4 acceptance (D-26).
- **Cover** (tier-independent, D-26): runner X is **covered** iff ∃ valid runner Y with `(l_Y − l_X) ∈ [cover_min_sl, cover_max_sl]` (closed; defaults **[0.3, 2.0] SL**) and `\|w_X − w_Y\| < cover_lat_sw` (default **0.8 SW** `[EG: OD-1x]`). Tier membership plays no role: tiers label states, geometry decides cover. The §3.4 minimum-duration smoothing applies to the cover predicate before classification.

### 2.3 Base-state taxonomy (exactly one per horse per charted frame)

Classification precedence is normative:

1. No supported detection for the runner (off-screen, occluded beyond EC-08 coasting, or detection absent) → `NOT_VISIBLE`.
2. Detection exists but projection confidence is below `min_state_conf` → `UNKNOWN`.
3. Otherwise classify exactly once from tier, cover and tier-relative order using the table below.
4. Compute overlays from §2.4 only after the base state; overlays MUST NOT replace it.

| State | Definition (pack-space) | Trot-lexicon anchor |
|-------|-------------------------|---------------------|
| `LEADER` | Tier 1, longitudinal rank 1 within tier 1, not covered. | « en tête » |
| `POCKET` | Tier 1, covered, exactly one tier-1 runner ahead. | « dans le dos du leader » |
| `RAIL_COVERED` | Tier 1, covered, ≥ 2 tier-1 runners ahead. | « le long de la corde » |
| `RAIL_UNCOVERED` | Tier 1, not covered, with ≥ 1 tier-1 runner ahead. | « à la corde, sans dos » |
| `OUTSIDE_COVERED` | Tier 2, covered. | « dans le dos, en dehors » |
| `PARKED` | Tier 2, **not** covered. `lead_uncovered_outside = true` for the uniquely furthest-advanced PARKED runner (positional sense: the parked runner furthest up the field *at this frame*; the move-detection event "first over" is out of scope, §12). If the top PARKED order is ambiguous under `rank_tie_sl`, all tied runners use `lead_uncovered_outside = NULL` and `lead_uncovered_outside_ambiguous = true`. At most one runner holds `lead_uncovered_outside = true` per frame. | « à l'extérieur sans abri » / « à hauteur de l'animateur » |
| `WIDE` | Tier ≥ 3, regardless of cover. Attributes `tier` and `covered` are recorded. | « trois de front / très large » |
| `NOT_VISIBLE` | No supported detection for the runner this frame. | — |
| `UNKNOWN` | Detection exists but projection confidence below `min_state_conf`. | — |

**Metric note (normative, D-27):** the headline metric (§6.2) measures the uncovered-outside *mask* (`tier ≥ 2 ∧ covered = false`), not the `PARKED` label; the label boundary (tier 2 vs ≥ 3) is categorical by design while the money metric is geometric. `[OPEN: RP-11]` Under tier-independent cover a tier-1 runner with no tier-1 runner ahead can be covered by an outside runner; this table has no row for it and implementations emit `UNKNOWN` with reason `table_gap_tier1_lead_covered` until the owner decides (recommended: keep `LEADER`, record `covered = true`).

**Design invariant (normative):** `LEADER` and `PARKED` are both uncovered but MUST remain distinct states — uncovered-by-choice at the front vs. uncovered-in-the-flow paying the aerodynamic/energetic toll. No aggregation may merge them upstream of feature engineering.

For every base state other than `NOT_VISIBLE` and `UNKNOWN`, boolean attribute `covered` MUST be recorded from §2.2. This is redundant for most states by design and preserves cover status for `WIDE`.

Segment `visibility ∈ {visible, not_visible, unknown}` is derived from the base state (`NOT_VISIBLE → not_visible`, `UNKNOWN → unknown`, all geometric states → visible). Camera-cut truncation is stored separately as booleans `start_truncated` / `end_truncated`; truncation MUST NOT be overloaded into `visibility`.

### 2.4 Overlay states (zero or more may co-exist with a base state)

| Overlay | Definition |
|---------|-----------|
| `BREAKING` | Active gait-break interval (event-driven, §4 M6). While active, the base state is still recorded if computable. |
| `DETACHED` | Pack geometry is coherent and the runner is separated at a longitudinal extreme by > `detach_sl`: `end = front` iff global rank 1 is > `detach_sl` ahead of global rank 2; `end = rear` iff the globally last runner is > `detach_sl` behind the immediately preceding runner. No overlay is emitted when the required neighboring runner is off-screen or geometry is invalid. In `start_format = volte_handicap` races, rear detachment near `t_0` is structurally induced by rendements: it is recorded unchanged and conditioned on `rendement_m` downstream (D-22). `DETACHED` is diagnostic in evaluation (D-28): excluded from the headline `rest` set, reported descriptively per stratum; detached *groups* (breakaway pairs) are out of scope (§12). |
| `LOW_CONF` | Projection valid but confidence in `[min_state_conf, ok_state_conf)`. |

### 2.5 Events (discrete, with attributes)

| Event | Attributes | v1 status |
|-------|-----------|-----------|
| `BREAK` | `t_start_frac`, nullable `t_end_frac`, nullable `positions_lost` (rank immediately after the end minus rank immediately before the start, valid only when both samples have valid order **and the visible-runner set is identical at both samples**, else NULL; positive means places lost; `positions_lost_basis_n` records the size of that visible set — D-31), `recovered ∈ {true, false, null}` (`true` = regained trot and remained classified ≥ `recover_window_s`; `false` = an observable outcome did not meet that stable-return rule; NULL = the recovery outcome is not observable), `review_status ∈ {pending, accepted, rejected}`, `human_confirmed` (derived bool: true iff accepted), `reviewed_at` | **In v1** |
| `STRETCH_BLOCK` | reserved | **Deferred v1.5** (§12) |
| `SHOT_GAP` | `t_start_frac`, `t_end_frac`, ordered `source_shot_types`, nullable `shot_type_before`, nullable `shot_type_after` for one maximal interval outside the configured shot type; boundary types are NULL at an anchor boundary | In v1 (QC-level event) |

For an accepted `BREAK`, `t_start_frac` is the first human-confirmed broken-gait frame and `t_end_frac` is the first supported return-to-trot frame. If no return is observable, `t_end_frac` remains NULL even when the runner is observed through a later terminal point. Event boundaries are reviewable outputs, not uneditable detector proposals. A break still open at `t_frac = 1.0` keeps `t_end_frac = NULL` and `recovered = NULL`; this is expected to coincide with a DAI and agents MUST NOT "fix" it (DR-10).

### 2.6 Race phases (config, informative defaults)

`early = [0, early_phase_end)`, `mid = [early_phase_end, late_phase_start)`, `late = [late_phase_start, 1.0]` of race elapsed, with informative defaults 0.30 / 0.72 (§7.1). Feature engineering downstream MAY re-bin; CV/human charts store raw fractions.

For video time `t_video_s`, `t_frac = (t_video_s - t0_video_s) / (tend_video_s - t0_video_s)`. CV/human chart rows are emitted only for `t_frac ∈ [0, 1]`; stored fractions are clamped only for floating-point epsilon, never to rescue a materially out-of-anchor timestamp.

`t_frac` is a **race-clock** fraction, not a per-runner course fraction: in `volte_handicap` races the same fraction is a different share of each runner's journey, and `late_phase_start` on a 2100 m autostart and a 2900 m handicap volte are different track positions. Downstream conditions on `base_distance_m`, `distance_run_m` and `piste`. Track-landmark detection stays banned; approximate track position is reconstructible downstream from `piste`, distance and RK (S-2, DR-07).

All segment/event intervals are half-open `[t_start_frac, t_end_frac)`, except an interval ending at the race finish may use `t_end_frac = 1.0`. Adjacent base segments meet without overlap or gap inside a charted interval.

---

## 3. Coordinate System & Geometry (normative)

### 3.1 Pack principal axis

Per frame, over all valid detections:

1. Collect centroids `c_i` (bbox center-bottom: mid-x, max-y of `horse_sulky` box — the point nearest the track plane).
2. Compute per-track motion vectors `v_i` over a `motion_window_s` (default 0.4 s) sliding window.
3. Unsigned principal axis = robust mean axis of `{v_i}` (outlier-trimmed, e.g. geometric median of unit vectors); fallback when motion degenerates (pack nearly stationary in frame due to camera tracking): PCA first component of `{c_i}`. Canonicalize the unsigned vector to point toward positive screen-x (or positive screen-y when x = 0).
4. Orient the axis as `u_long` using persisted `travel_direction_sign ∈ {-1, +1}` relative to that canonical vector. The unsigned axis MUST be temporally smoothed across frames (`axis_smooth_s`) and estimated from displacements longer than `axis_min_vector_sl`·SL with length weighting: lateral coordinates are extremely sensitive to axis error — a tilt δ displaces a runner `l` SL back by ≈ `(SL/SW)·l·sin δ` SW, so with `sw_ratio = 0.35` a 5 SL pack needs ≈ 1° axis accuracy for `same_tier_sw = 0.6` to separate lanes (RP-21). A single frame's motion estimate MUST NOT set the axis on its own. Majority image motion supplies only a heuristic proposal because camera pan can reverse apparent drift; a low-confidence or changed proposal MUST be human-confirmed in the seeding tool. Missing orientation calibration makes M4 confidence zero for that shot.
5. `u_lat` = perpendicular to `u_long`, sign chosen so that **increasing lateral coordinate = away from the rail**. `rail_side ∈ {left_of_travel, right_of_travel}` is calibrated per charted shot (heuristic: the lower on-screen tier-1 line in the Vincennes wide pan) under the same confirm-on-low-confidence/change rule.

### 3.2 Projection and units

- Longitudinal coordinate: `l_i = c_i · u_long`; lateral: `w_i = c_i · u_lat`.
- All distances normalized by **SL** (current-frame median bbox long side). Lateral thresholds use **SW = SL × sw_ratio**.
- Per-frame geometry outputs: `(l_i/SL, w_i/SW, rank_long, tier_cluster, tier, order_ambiguous, rail_ref_w_sw, rail_ref_conf, conf)` per runner.

### 3.3 Prohibitions

- Pixel-count thresholds anywhere outside SL/SW normalization: **banned**.
- Homography to metric track coordinates: **banned in v1** (out of scope §12; only reconsidered if GPS/sectional calibration data ever materializes).
- Y-coordinate-as-depth heuristics: **banned** (superseded by pack-space projection).

`[OPEN: RP-19/RP-22/RP-23 — owner decision]` The world-space simulator study (`docs/research/11-simulated-geometry.md`) shows that from an elevated side-on camera lateral metres project at roughly height/depth of longitudinal metres, so `SW = SL·sw_ratio` merges adjacent lanes by construction, that the §3.1 motion axis is biased by pan/zoom even without jitter, and that the `(mid-x, max-y)` centroid carries a pan-dependent lateral bias. Three options are implemented in the reference projector and proposed for adoption: (a) `axis_source = rail` — the projected rail-line direction as the primary axis, never smoothed; (b) `lateral_scale_mode = rail_fence_projective` — a 1-D projective lateral coordinate from the rail line, the fence line and their vanishing point (horizon assumed horizontal; needs `track_width_sl` `[EG]`), with each runner measured against the nearest rail/fence polyline segment on bends; (c) a foot-point correction (`vehicle_half_width_sw`) from the bbox bottom edge to the vehicle centre line. (b) is not a homography to track coordinates and would need an explicit carve-out in this section. Lateral resolvability remains bounded by the covering camera's elevation per track section (RP-24).

### 3.4 Temporal smoothing

Raw per-frame states MUST be smoothed before segment emission:

- Minimum segment duration `min_state_s` (default 1.0 s); shorter runs **between confident geometric base states** are merged into neighbors by confidence-weighted vote.
- Hysteresis on tier transitions: a tier change must persist `tier_hysteresis_s` (default 0.6 s) to commit.
- `NOT_VISIBLE` and `UNKNOWN` base segments, `SHOT_GAP` events, and confirmed `BREAKING` overlays MUST retain their observed boundaries and MUST NOT be merged away or interpolated across. Other overlay types are smoothed independently; event-derived `BREAKING` is never smoothed.
- Derived attributes are recomputed after smoothing. In particular, at most one co-timed `PARKED` segment may have `lead_uncovered_outside = true`.
- Smoothing parameters are part of the threshold set (§7).

---

## 4. Module Contracts M0–M8 (normative)

### 4.0 Build order and gating

```
M0 → M1 → M2 → M3(+seeding tool) → M4 → M5 → M6 → M7 → M8
```

| Gate | Rule |
|------|------|
| G-1 | M2 MUST NOT start until M1 passes its acceptance test on the OD-1 sample replays. |
| G-2 | M4 MUST NOT start until M3 produces ID-assigned tracklets on ≥ 3 **dev** golden races within the human budget. |
| G-3 | M5 MUST NOT start until M4 passes its acceptance test on **dev** golden races. |
| G-4 | DoD evaluation (§0.2) MUST use only pipeline runs where M7 gates were active. |

Each module: **Input contract → Output contract → Acceptance test → Definition of done.** Storage details for all outputs: §9. All module outputs MUST carry `extractor_version`, `threshold_set_version`, and the upstream artifact IDs they were derived from.

### M0 — Ingest & Normalization

| | |
|---|---|
| **Input** | Raw replay video file; race metadata record (`race_id`, date, meeting, race no., `base_distance_m`, `start_type ∈ {volte, autostart}`, `start_format ∈ {autostart, volte_flat, volte_handicap}`, `piste ∈ {GP, PP}` (from ingest, never inferred from distance — DR-06), declared runners with saddle numbers, per-runner `distance_run_m` and `autostart_row ∈ {1, 2, NULL}` (DR-04), official finish order, per-runner official time fields with raw source strings preserved, non-partants, DAI/DQ list, arrival-revision evidence when available). |
| **Output** | Normalized CFR video at `normalized_fps`, preserving source width/height/aspect ratio; persisted source + normalized ffprobe metadata; `races` + `runners` rows normalized per the metadata rules below; source and normalized file hashes. Frame selection at target timestamps is deterministic; synthetic motion interpolation is forbidden. |
| **Acceptance** | Given 3 sample replays: normalized outputs exist, metadata joined, duration differs from decoded source by ≤ 1 normalized frame, and hashes are stable across re-runs under the same extractor environment. Metadata-normalization unit tests cover: 2100 m autostart; 2850 m flat volte; 2850/2875/2900 handicap volte whose winner started at 2900 m (that runner's `official_elapsed_norm_s` MUST use 2900 m); an elapsed field duplicating the km rate; disagreeing time fields; a malformed row (e.g. elapsed `242` with km rate `120` → `unavailable` + `time_fields_disagree`); a winner with no published time (race-level method resolves `unavailable` in M3). |
| **DoD** | Idempotent re-ingest (same source hash → no duplicate rows). Corrupt/partial files flagged `ingest_failed`, never silently truncated. Normalization command, ffmpeg build hash and codec parameters are recorded under `producer_version`. |

**M0 metadata normalization (normative):**

1. **Distances.** Every declared runner carries `distance_run_m ≥ base_distance_m`; `rendement_m = distance_run_m − base_distance_m`. Missing or negative values → `ingest_failed`; inference is banned. `rendement_m` SHOULD be a multiple of 25 m; a violation appends `rendement_not_25m` to `metadata_conflict_codes` without blocking ingest.
2. **Start-format invariants.** `start_type = autostart ⇔ start_format = autostart`; `start_format ∈ {autostart, volte_flat}` ⇒ all `rendement_m = 0`; `start_format = volte_handicap ⇔ ∃ rendement_m > 0`; `start_handicap := (start_format = volte_handicap)`. Any contradiction → `ingest_failed`.
3. **Times.** Per-runner elapsed (`official_elapsed_s`) and km rate (`official_km_rate_s`) are parsed where published; raw source strings are preserved with unit provenance. Unit guessing is fabrication (prime directive).
4. **Per-runner time normalization**, computed in M0 for every declared runner with NO dependency on first-past resolution, producing `time_normalization_status ∈ {direct_elapsed, km_rate_derived, unavailable}`:
   - both fields present and `|elapsed − km_rate × distance_run_m / 1000| ≤ time_unit_consistency_tol_s` → `direct_elapsed`;
   - both present and `|elapsed − km_rate| ≤ time_unit_consistency_tol_s` (the "elapsed" field duplicates the km rate) → `km_rate_derived`, append `elapsed_is_km_rate`;
   - both present, neither consistency holds → `unavailable`, append `time_fields_disagree`;
   - exactly one field present → use it only if the implied km rate `elapsed × 1000 / distance_run_m` (resp. `km_rate` directly) lies in `[plausible_km_rate_min_s, plausible_km_rate_max_s]`: elapsed-only and plausible → `direct_elapsed`; km-rate-only and plausible → `km_rate_derived` (S-3); else `unavailable` with `elapsed_implausible` / `km_rate_implausible`;
   - no field available → `unavailable` with **no** conflict code (expected for NP/DAI/unresulted runners).

   The default `time_unit_consistency_tol_s = 0.5` is deliberate: an order of magnitude above the observed direct-vs-derived quantization ceiling (≤ 0.21 s in the reference corpus) and well below one 25 m rendement step (≈ 1.8–1.9 s at typical km rates). A wrong `distance_run_m` band therefore fails consistency at ingest instead of passing silently; `time_fields_disagree` on an otherwise well-formed runner is a distance-band suspect.
5. **Normalized total.** `official_elapsed_norm_s` := the parsed elapsed on `direct_elapsed`; `official_km_rate_s × distance_run_m / 1000` on `km_rate_derived`; NULL on `unavailable`. Every downstream consumer (EC-10, EC-12, M3) MUST read `official_elapsed_norm_s`, never the raw parsed fields. Race-level `official_time_method` is NOT computed in M0: M3 resolves it as `time_normalization_status(first_past_saddle_no)` and persists it on `race_anchors` (D-25).
6. `metadata_conflict_codes` is a closed lex-sorted set in v1: `{elapsed_implausible, elapsed_is_km_rate, km_rate_implausible, rendement_not_25m, time_fields_disagree}`. Extensions are minor version bumps.

### M1 — Shot Segmenter

| | |
|---|---|
| **Input** | Normalized video. |
| **Output** | `shots` rows: `(shot_id, type ∈ {wide_pan, head_on, tight, replay_insert, graphic_fullscreen, other}, t_start_video_s, t_end_video_s, confidence, graphic_overlay_mask_ref)`. Base shot intervals are contiguous, non-overlapping and cover the full video; `graphic_overlay_mask_ref` is a nullable pointer to a frame-indexed mask artifact and may coexist with `wide_pan`. |
| **Acceptance** | On OD-1 samples with human-labeled shot boundaries: boundary detection F1 ≥ 0.90 (±0.5 s tolerance); wide-pan classification accuracy ≥ 0.95. Any learned M1 component uses leave-one-race-out evaluation across OD-1, with thresholds fixed inside each training fold. On annotated wide-pan graphic frames, graphic-overlay mask F1 ≥ 0.90 and runner-footprint occlusion recall ≥ 0.90; if OD-1 supplies fewer than 100 affected frames, the M1 fixture set MUST be extended before acceptance. |
| **DoD** | `replay_insert` (in-broadcast replays) reliably separated from live footage (EC-07) — charting a replay twice is a corpus-poisoning bug, hence the dedicated class. Low-confidence base segments default to `other` (= not charted), per prime directive. Graphic overlays remain masks/attributes and MUST NOT change a `wide_pan` base label. |

### M2 — Detection

| | |
|---|---|
| **Input** | Frames from `wide_pan` segments only (gated by M1). |
| **Output** | Per frame: `horse_sulky` bboxes with confidence. Single class in v1. |
| **Acceptance** | On the detector-heldout dev fixture (§6.1; ≥ 500 frames across ≥ 5 races, day and night strata): AP@0.5 ≥ 0.90; per-frame recall of visible runners ≥ 0.95 in fields ≤ 14. The split is by race: no frame from a detector-heldout race may appear in detector training, augmentation-source pools or threshold tuning. This fixture is not the sealed 10-race system holdout. |
| **DoD** | Trained/validated on both day and floodlit night footage (EC-05). Inference faster than real-time × 4 on owner hardware (soft target, informative). |

### M3 — Tracking + Seeding Tool

| | |
|---|---|
| **Input** | M2 detections per wide-pan segment. |
| **Output** | `tracklets` (tracker IDs, per-frame boxes); `id_assignments` rows `(tracklet_id → saddle_no, method ∈ {human_seed, propagation, human_correction}, human_confirmed)`; one `race_anchors` row; one `shot_calibrations` row per charted wide-pan segment. Post-hoc start/finish observations write only QC statuses and MUST NOT be an identity-assignment method (D-01). |
| **Acceptance** | On dev golden races: identity assignments pass the sampled protocol in §6.4; ID swaps per race requiring re-seed ≤ 8 median; both anchors and all charted-shot orientation calibrations persist, and anchors pass EC-12 sanity. A synthetic relegation fixture (first past the post later rétrogradé) MUST keep `t_end` on the first-past runner, resolve the finish check `inconclusive` without `id_suspect`, and record `finish_check_basis = final_revision_carveout`; `first_past_method` MUST resolve via `observed_crossing` or `human_confirm`, never `official_assumed`. A second synthetic fixture (head-on finish, zero observed crossings, no revision evidence) MUST resolve `first_past_saddle_no = NULL` with `anchor_check_status = inconclusive`, never `official_assumed` (D-30). |
| **DoD (tool)** | Keyboard-driven frame-stepper (CLI + OpenCV window grade, D-16): play/pause/step, configurable **≥ 2× auto-play with automatic slowdown at flagged events** (DR-12), click-runner→type-saddle-number, jump-to-next-flagged-cut, a "possible recall" flag surfaced when EC-14 heuristics fire, one-key confirmation of proposed travel-direction + rail-side orientation for the initial segment and any later segment whose heuristic is low-confidence or changes (§3.1), correction keys for either component, one-key `t_0`/`t_end` anchor capture (D-10), one-key break-candidate confirm/reject (M6 loop), one-key first-past confirmation and arrival-revision adjudication prompts when required by DoD (a), per-race human-time logged automatically (feeds DoD-3). |
| **DoD (logic)** | Consistency checks are non-corrective. **(a) Finish/crossing check (D-23/D-25).** `t_end` anchors on the first past the post. The reference crossing order is provisional/photo order when ingested; otherwise the official final order restricted to runners not known to be revision-implicated (`arrival_revision_type ∈ {none, unknown}`), always excluding NP/DAI/DQ runners. `finish_check_basis ∈ {provisional, final_unrevised, final_assumed, final_revision_carveout, unavailable}` is recorded: `provisional` when a provisional order was ingested; `final_unrevised` iff `arrival_revised = false`; `final_assumed` when the reference contains `unknown`-status runners; `final_revision_carveout` when known revision-implicated runners were excluded; `unavailable` otherwise. Reconstruct **visibly observed finish crossings** across the finish shot and compare only runners present in the reference — never the full-field order at the instant the first-past runner finishes. A contradiction attributable only to excluded or revision-implicated runners resolves to `inconclusive`. When `arrival_revised` is NULL and a contradiction is observed, the tool pauses for human adjudication (wall-clock logged in human-minutes): a confirmed identity error → `mismatch` + `id_suspect = true`; a confirmed or plausible arrival revision → set the revision fields and resolve `inconclusive`. `first_past_saddle_no` resolution ladder (D-25): (i) finish-line coverage begins before the first crossing and that runner is identified → `first_past_method = observed_crossing`; (ii) otherwise the official winner is adopted iff the crossing reconstruction observes **≥ `finish_evidence_min_k` crossings** (default 3 `[EG: OD-1x]`), all consistent with the reference order, and no revision evidence exists — `official_unrevised` when `arrival_revised = false` (authoritative source), `official_assumed` when `arrival_revised` is NULL (zero extra operator cost; the mandatory reconstruction is the corroborator); zero or insufficient observed crossings → `first_past_saddle_no = NULL` and EC-12 `inconclusive` — a corroborator with no observations is not a corroborator (D-30); `race_anchors.finish_evidence_n` records the count; (iii) contradiction or revision evidence → adjudication → `human_confirm`; (iv) unresolvable → NULL and EC-12 becomes `inconclusive`. `arrival_revised` MUST NOT be defaulted to `false`. M3 then persists `official_time_method := time_normalization_status(first_past_saddle_no)` on `race_anchors` (`unavailable` when `first_past_saddle_no` is NULL). **(b) Start check.** Compare the initial visible lineup against start structure: official autostart lanes — for fields > 9 the autostart is modelled as two rows: front-row lateral order = post order, second row checked for presence only, never order (DR-04) — or volte rendement **bands at their marks** — each visible runner MUST belong to its band's longitudinal cluster and band clusters MUST order by mark; within-band order is never inferred. Poor band separation or insufficient evidence → `inconclusive`. Each status is in `{pass, mismatch, inconclusive}`; contradictions set the corresponding `{finish,start}_check_status = mismatch` and `id_suspect = true`, never auto-corrected. Live non-wide-pan start/finish shots MAY be inspected solely for these QC checks; they MUST NOT produce tracklets or state segments (D-02). |

### M4 — Pack-Space Geometry

| | |
|---|---|
| **Input** | ID-assigned tracklets + wide-pan frames + per-shot orientation calibration (`travel_direction_sign`, `rail_side`). |
| **Output** | Per frame per runner: `(l_sl, w_sw, rank_long, tier_cluster, tier, order_ambiguous, rail_ref_w_sw, rail_ref_conf, conf)` per §2.2/§3. |
| **Acceptance** | On dev golden frames with human-labeled tier/order and rail-reference validity (≥ 300 frames): longitudinal-order agreement ≥ 0.97 (pairwise; human-labeled ties scored as correct only when emitted `order_ambiguous`); tier agreement ≥ 0.92; valid-vs-unresolved rail-reference F1 ≥ 0.90. |
| **DoD** | Degenerate-geometry frames (pack < 3 visible, principal axis unstable, or rail reference invalid for absolute tiering) emit `conf = 0` → downstream `UNKNOWN`, never guessed. Longitudinal near-ties set `order_ambiguous`; M5 applies the base-state vs. first-over rules in §2.2. |

### M5 — State Machine

| | |
|---|---|
| **Input** | M4 per-frame geometry. |
| **Output** | Base-state segments plus geometric overlays `DETACHED` and `LOW_CONF` per §2.3–2.4, smoothed per §3.4, with `state_kind ∈ {base, overlay}`, `covered`, `lead_uncovered_outside`, `lead_uncovered_outside_ambiguous`, `confidence`, `visibility`, `start_truncated` and `end_truncated`. `BREAKING` is appended by M6 after confirmation. |
| **Acceptance** | On dev hand charts: macro base-state segment IoU ≥ 0.80; both the uncovered-outside mask IoU and the covered-mask IoU ≥ 0.85 (definitions §6.2–6.3; pre-calibration targets, final numbers via §7). |
| **DoD** | Exhaustive per-frame classification: every (runner, frame) in a charted interval maps to exactly one base state (incl. `NOT_VISIBLE`/`UNKNOWN`); overlays independent; state-machine transitions unit-tested against synthetic trajectories (crossing, rail-uncovered gaps, front/rear detachment, short occlusion, tier drift and first-over changes). |

### M6 — Break / Event Detection

| | |
|---|---|
| **Input** | M4 geometry series + M2 bbox series (aspect/oscillation signals). |
| **Output** | `events` rows: `BREAK` candidates with attributes per §2.5 and initial `review_status = pending`; the M3-owned review surface, invoked after M6 candidate generation, changes status to `accepted` or `rejected`. An accepted event with known end appends a coextensive `BREAKING` overlay interval, serialized as one or more adjacent segments when inherited payload attributes change (§9). If the end is unobservable, the overlay ends at the last supported frame with `end_truncated = true` while event `t_end_frac` remains NULL. Rejected candidates remain auditable but append no overlay. |
| **Acceptance** | Candidate recall ≥ 0.80 vs. hand-charted breaks on dev set; candidate volume ≤ 4 per M6-evaluable attempt median (definition §6.2), including attempts that later fail Q-1, Q-2, Q-4, Q-5 or Q-7 (false-positive load must not blow the 5-min budget). |
| **DoD** | Detection signal = longitudinal-rank velocity anomaly + bbox vertical-oscillation regime change (features config-exposed); DAI cross-check: officially sanctioned DAI runners SHOULD have ≥ 1 candidate — misses logged as `dai_uncaught_break_expected`, or as `dai_gait_other` when the sanction concerned another gait (amble / traquenard; human tag at review); §7 calibration MUST NOT tune break thresholds against `dai_gait_other` (DR-09). Only `accepted` events have `human_confirmed = true` or produce `BREAKING`; pending and rejected candidates remain distinct for load/audit metrics. |

### M7 — QC & Coverage

| | |
|---|---|
| **Input** | All upstream outputs for a race. |
| **Output** | One race-level `qc` row plus one `runner_qc` row per declared non-NP runner, and one `SHOT_GAP` event per maximal anchored M1 interval outside the configured shot type. Race QC carries wide-pan coverage fractions, human-minutes, day/night stratum, `chartable ∈ {true, false}` and enumerated failure codes; runner QC carries visible and stateable time fractions, occlusion counts and terminal status. |
| **Acceptance** | Gate logic unit-tested; a synthetic race violating each §10 gate is correctly excluded; anchored non-charted intervals produce complete, non-overlapping `SHOT_GAP` events without state interpolation. |
| **DoD** | Read APIs and exports exclude `unchartable` races by default. Raw state segments may be fetched only with explicit `include_unchartable=true`; the override is diagnostic-only and MUST NOT be accepted by feature-export entry points (D-11 enforced structurally). |

### M8 — Storage & Versioning

| | |
|---|---|
| **Input** | All module outputs. |
| **Output** | Persistent store per §9 schema; export views for feature engineering. |
| **Acceptance** | Round-trip integrity test; the canonical export (stable row/column ordering, operational fields such as `created_at` excluded) is byte-identical under the same inputs and versions (DoD-5); two extractor versions coexist queryably on the same race. |
| **DoD** | Migration procedure documented for schema-additive changes (new columns = minor version; breaking = major). Default export views join `qc.chartable = true`; no feature-export path exposes the diagnostic override. |

---

## 5. Human Workflow & Budgets (normative)

### 5.1 Per-race operator loop (target median ≤ 5 min, cap 8 min `[EG]`; D-09, D-29)

1. Open race in seeding tool → confirm the initial wide-pan segment's proposed travel-direction + rail-side orientation (1 key when both are correct).
2. Mark `t_0` and `t_end` anchors (2 clicks; volte vs. autostart semantics per EC-04).
3. Initial seed on first stable wide-pan frame: click each runner → saddle number.
4. Tool auto-plays at ≥ 2× with automatic slowdown at flagged events (DR-12); pauses at flagged cuts / tracker-confidence drops → confirm/correct orientation only when the new segment's heuristic is low-confidence or changes, and re-seed only flagged runners.
5. Review break candidates (accept/reject, 1 key each).
6. Tool writes chart + QC + logged human-minutes.

**Budget rule:** wall-clock over `human_budget_cap_min` (8 min `[EG: ≈ p90 of pilot]`, D-29) → race flagged `over_budget` and `chartable = false`; operator MAY finish the current race for diagnosis but it remains excluded from default outputs. Repeated over-budget races indicate a tooling or corpus problem to fix at the module level — not by working harder (skip-don't-rescue, D-09). Arrival-revision adjudication under M3 DoD (a) is an operator action; its wall-clock counts toward logged human-minutes.

An **eligible race attempt** is a race satisfying the static v1 corpus rules (Vincennes, attelé, field size ≤ 14) whose video passes M0 ingest and enters the M3 operator loop. Once entered, the attempt remains in Human-minutes and candidate-load denominators even if it later fails Q-1 through Q-5 or Q-7. Races rejected before the loop for corrupt ingest, wrong track/discipline or oversized field are not attempts.

### 5.2 Hand-charting protocol (ground truth, OD-3)

- Charted in the **same schema** (§2), using a chart template (state timeline per runner at 1-s resolution or segment notation, charter's choice — stored as segments).
- Charter watches the replay at ≤ 1× speed with pause and applies the same shot gate as M1. Inside a charted wide-pan interval, an individually off-screen/occluded runner is `NOT_VISIBLE`; outside the configured shot type, record `SHOT_GAP` and no base-state segment. Humans MUST NOT bridge either kind of gap by inference.
- A hand-charted `BREAK` truth is written to `events` with `method = human_chart`, `review_status = accepted` and `human_confirmed = true`; it is independent of machine candidate generation.
- Each race's hand chart records charter time spent (calibrates future corpus decisions).
- Dev/held-out split (30/10) is fixed in the golden manifest before charting. The manifest is authoritative for `split`; `hand_charts.split` is a denormalized copy validated at write time, and a mismatch rejects the write (S-6). After a held-out hand chart is completed, its replay and chart are sealed and MUST NOT be reopened for module development, threshold tuning or error analysis until a declared version-freeze evaluation.

### 5.3 Roles

Single-operator project. Where this spec says "human", it means the project owner. All human actions are logged with timestamps (auditability + budget tracking).

---

## 6. Golden Data & Acceptance (normative)

### 6.1 Golden fixtures

- **Tier A (OD-1):** 3 sample replays, inspected and shot-labeled. Purpose: falsify camera assumptions; M1 acceptance.
- **Tier B (OD-3):** 40 hand-charted races (30 dev / 10 held-out), Vincennes attelé, ≤ 14 runners, mixed day/night, mixed distance bands and start formats, drawn from the meetings the owner actually bets. The manifest records `start_format` and `piste` per race; ≥ 5 dev and ≥ 2 held-out races MUST be `volte_handicap`; held-out SHOULD cover both pistes and both day/night strata present in the candidate pool. The completed annotations MUST contain ≥ 20 observable `BREAK` starts in dev and ≥ 10 in held-out; otherwise break recall is not statistically eligible for acceptance and a manifest revision is required.
- **Tier B frame fixtures (also OD-3):** from the 30 system-dev races, reserve ≥ 500 M2 bbox-labeled frames across ≥ 5 races as a detector-only race-disjoint holdout, and label ≥ 300 frames for M4 tier/order/rail-reference acceptance. Detector-heldout races remain system-dev races; they MUST NOT be confused with or drawn from the sealed 10-race system holdout. Training annotations are additional and MUST remain disjoint from the detector holdout by race.
- Golden race selection SHOULD over-sample v1 signal-rich races (clear parked trips, covered/wide transitions, detached runners, breaks with recovery) but MUST include ≥ 10 "boring" races to measure false-positive behavior. `STRETCH_BLOCK` is not charted or scored before v1.5.
- Before charting or calibration, persist a versioned golden-fixture manifest containing race IDs, selection strata, dev/held-out assignment, assignment seed and source hashes. Replacements require a recorded reason and a new manifest version; held-out membership MUST NOT be silently changed.

### 6.2 Metrics

| Metric | Definition |
|--------|-----------|
| **Segment IoU (per state)** | For runner r, state s: `duration(T_pred ∩ T_true) / duration(T_pred ∪ T_true)` over charted time; averaged over runners, then races. The evaluation mask is time where the hand chart marks the runner observable and M1 marks the configured shot type present; predicted `NOT_VISIBLE`/`UNKNOWN` remains inside that mask and therefore counts as a miss. |
| **Macro base-state IoU** | Unweighted mean of per-state Segment IoU over `{LEADER, POCKET, RAIL_COVERED, RAIL_UNCOVERED, OUTSIDE_COVERED, PARKED, WIDE}`; a state absent from both prediction and truth for an entire race is omitted for that race. |
| **Covered-mask IoU** | `duration(T_pred(covered=true) ∩ T_true(covered=true)) / duration(T_pred(covered=true) ∪ T_true(covered=true))` over the same visibility mask. This positive-class mask score uses the `covered` attribute and therefore includes covered `WIDE` intervals; it is not a macro-average over the covered and uncovered classes. |
| **Confusion matrix** | Frame-level (1 Hz resample) base-state confusion, per race and pooled. |
| **Uncovered-outside mask IoU** | Same construction as the covered mask over `tier ≥ 2 ∧ covered = false` (`PARKED`, and `WIDE` with `covered = false`). The money mask (D-27). |
| **Weighted headline score** | `0.5·IoU(uncovered-outside mask) + 0.3·IoU(covered mask) + 0.2·MacroIoU(rest)`, where `rest = {LEADER, RAIL_UNCOVERED, WIDE}`; `DETACHED` is reported descriptively per stratum, outside the headline (D-28). Reported both with and without Q-7 failures (D-35). This is the number quoted as "extractor accuracy"; DoD-1 additionally requires the two mask floors stated there. |
| **Chartable rate (per stratum)** | Share of eligible attempts with `chartable = true`, overall and per stratum (day/night × field-size band × `start_format` × `piste`). Review trigger: any stratum below `stratum_yield_review_factor` × overall (0.5 `[EG]`) → manifest/threshold review before further charting (D-35). |
| **Segmental edit score, F1@{10, 25, 50}** (descriptive) | Lea et al. (2017) conventions over per-runner base-state sequences; reported next to Segment IoU to expose over-segmentation. Never a floor. |
| **Break recall / candidate load** | Recall is measured on all machine-generated candidates **before** human filtering against hand-charted breaks whose starts are observable inside the configured shot type. A candidate matches when start times differ by ≤ `break_match_tolerance_s`, using one-to-one minimum-time-distance matching; one candidate cannot satisfy two truths. Candidate load counts all generated candidates regardless of final `review_status` and is summarized per **M6-evaluable attempt**: an eligible attempt (§5.1) with valid timeline anchors that reaches M6 inference. Human-confirmed event precision is reported descriptively but has no v1 floor. |
| **Human-minutes** | Median per eligible attempted race, including `over_budget` exclusions (DoD-3). |

For any IoU component, a runner/race sample with an empty prediction-and-truth union is omitted rather than scored as 1. If a **DoD-1 component** (either mask IoU) has an empty union across the entire evaluation set, the evaluation is invalid and the golden fixtures MUST be revised; any other component is simply omitted for that set (D-28).

### 6.3 Evaluation rules

- Held-out races evaluated only at declared version freezes; results logged to the changelog with `extractor_version` + `threshold_set_version`.
- State-accuracy and break-recall evaluations on races that fail Q-1 through Q-6 are void. Human-minutes includes every eligible attempt, even one later failing Q-1 through Q-5 or Q-7. Candidate load includes every M6-evaluable attempt, even one later failing Q-1, Q-2, Q-4, Q-5 or Q-7. A failed downstream gate MUST NOT selectively remove a difficult attempt from either operational denominator.
- DoD-1/2 evaluation is invalid unless DoD-6 is met. Break recall is additionally invalid unless the held-out truth contains ≥ 10 observable break starts (§6.1); an empty or undersized event set cannot pass by convention.
- The visibility mask is defined from hand-chart observability and pipeline shot coverage before state comparison; predicted `NOT_VISIBLE`/`UNKNOWN` intervals are reported separately as coverage/abstention and MUST NOT be silently deleted from their denominators.
- Per-stratum reporting REQUIRED: day vs. night, field size bands (≤ 10, 11–14), `start_format`, `piste`.
- Q-7 (`over_budget`) is deliberately excluded from the accuracy-voiding list: extractor accuracy and operational yield are different questions. The headline is therefore reported both with and without Q-7 failures (F-8, D-35). DoD-2 is reported as a point estimate with its Wilson 95% interval (D-31).

### 6.4 Spot-check protocol (M3 identity audit)

Per audited race: sample 12 timestamps **stratified across 4 equal phase bins of `[t_0, t_end]`** (3 per bin), and at each timestamp 3 visible runners resampled without replacement where possible; human verifies saddle-number correctness in the tool. The RNG seed (`SHA-256(race_id | extractor_version | "identity-audit-v1")`) and sampled coordinates are persisted. At least 35/36 correct = pass. The sampled points MUST touch ≥ 8 distinct tracklet intervals, otherwise the audit reports its effective n (identity errors persist along a tracklet, so 36 samples are far fewer than 36 independent trials). **Operating characteristic (informative):** under independence the rule accepts a race with 0.99 per-sample identity accuracy w.p. ≈ 0.95, 0.98 w.p. ≈ 0.84 and 0.95 w.p. ≈ 0.46 — the audit is a smoke test, not a certificate (D-31). The pooled exact rate and per-race counts MUST be reported; this is a sampled identity estimate, not a claim that every unsampled frame was inspected.

---

## 7. Calibration Procedure (normative)

Thresholds are a **versioned artifact** (`threshold_set_version`), never constants in code (D-18).

### 7.1 Threshold registry (initial defaults)

| Key | Default | Used in |
|-----|---------|---------|
| `sw_ratio` | 0.35 | §2.1 |
| `normalized_fps` | 25.0 `[EG: OD-1x]` | M0 |
| `same_tier_sw` | 0.6 `[EG: OD-1x sanity]` | §2.2 |
| `max_tier_span_sw` | 1.2 `[EG: OD-1x]` | §2.2 (D-26) |
| `rail_ref_conf_min` | 0.5 | EC-13 (M4 rail-reference confidence; module default) |
| `axis_neighbourhood_k` | 0 `[EG: OD-1x bend frame]` | §3.1 (0 = whole-pack axis; RP-20) |
| `axis_min_vector_sl` / `axis_smooth_s` | 0.05 / 1.0 | §3.1 motion-axis jitter guard and temporal smoothing (RP-21) |
| `lateral_scale_mode` / `track_width_sl` | sw_ratio / 5.8 `[EG: track plan]` | §3.2 lateral scale; `rail_fence` = two track lines at known separation (RP-19, `[OPEN]`) |
| `rail_lane_center_offset_sw` | 0.5 | §2.2 |
| `rail_attach_sw` | 1.0 | §2.2 / EC-13 |
| `rank_tie_sl` | 0.10 | §2.2 / §2.3 |
| `cover_min_sl` / `cover_max_sl` | 0.3 / 2.0 | §2.2 |
| `cover_lat_sw` | 0.8 `[EG: OD-1x]` | §2.2 (D-26) |
| `detach_sl` | 6.0 | §2.4 |
| `min_state_s` | 1.0 | §3.4 |
| `tier_hysteresis_s` | 0.6 | §3.4 |
| `motion_window_s` | 0.4 | §3.1 |
| `min_state_conf` / `ok_state_conf` | 0.3 / 0.6 | §2.3–2.4 |
| `recover_window_s` | 5.0 | §2.5 |
| `break_match_tolerance_s` | 2.0 | §6.2 / M6 acceptance |
| `anchor_offset_volte_s` / `anchor_offset_autostart_s` | 0.0 / 0.0 `[EG: OD-1x]` | EC-12 (D-34) |
| `anchor_tol_volte_s` / `anchor_tol_autostart_s` | 2.0 / 2.0 `[EG: OD-1x]` | EC-12 / Q-3 (D-34) |
| `finish_evidence_min_k` | 3 `[EG: OD-1x]` | M3 DoD (a) rung (ii) (D-30) |
| `human_budget_cap_min` | 8 `[EG: pilot ≈ p90]` | §5.1 / Q-7 (D-29) |
| `stratum_yield_review_factor` | 0.5 `[EG]` | §6.2 chartable rate (D-35) |
| `time_unit_consistency_tol_s` | 0.5 | M0 metadata normalization |
| `plausible_km_rate_min_s` / `plausible_km_rate_max_s` | 65 / 110 | M0 metadata normalization (S-5: 55 never bound; attelé record RK ≈ 69 s/km) |
| `early_phase_end` / `late_phase_start` | 0.30 / 0.72 | §2.6 |
| `coverage_race_min` / `coverage_final_third_min` | 0.65 / 0.70 | §10 Q-1/Q-2 |
| `graphic_occlusion_max` | 0.15 | EC-06, Q-5 |
| `occl_max_s` | 1.5 | EC-08 |
| M6 break-detector params | (module-defined, config-exposed) | M6 |

Machine copy: `config/thresholds/TS-0.0.0-provisional.yaml` (module namespaces `m1_shots`, `m2_detect`, `m3_track`, `m6_events` hold module defaults, tuned in §7.2). This table is the mandatory minimum registry, not permission for hidden module constants. Before a module can pass acceptance, every numeric cutoff that can change emitted artifacts (shot confidence, detection/NMS, tracker coasting/re-association, geometry stability, state/event logic) MUST appear under a namespaced key in the same threshold-set YAML. Model weights and non-numeric implementation choices belong to `extractor_version`, not the threshold set.

### 7.2 Procedure

1. Freeze dev/held-out split (§5.2) **first**.
2. Grid or Bayesian search over the registry against **dev** hand charts, objective = weighted headline score (§6.2), constraints = the M5 component floors and M6 candidate load.
3. Freeze winner as `threshold_set_version = TS-x.y`; record search space + objective in the changelog.
4. Report once on **held-out**. No iterating against held-out; if held-out collapses vs. dev (> 10 pt gap), the state definitions — not just thresholds — are suspect: open a spec revision.
5. Every CV-produced chart row stores the TS version that produced it; recalibration re-runs the corpus under the new TS paired with the applicable existing or new extractor version (M8 supports coexistence).

---

## 8. Edge-Case Registry (normative, living section — D-19)

Owner-extensible. Rules for extension: new entries get the next `EC-nn` number; each entry MUST specify all four columns; mandated behavior defaults to **flag and degrade, never guess**. Agents MUST implement every entry whose module is in scope of their task. Changes here are minor-version bumps.

| ID | Trigger | Detection heuristic | Mandated behavior | QC field |
|----|---------|--------------------|--------------------|----------|
| EC-01 | Camera cut mid-move (wide-pan interrupted during a state transition) | M1 boundary inside an open state segment | Close segment at cut with `end_truncated = true`; new segment on resume with `start_truncated = true`; no interpolation across the gap | `n_truncated_segments` |
| EC-02 | Pack split beyond frame (leaders and tail not simultaneously visible in wide pan) | Tracked-runner count < active runners while M2 recall is nominal and tracks exit at frame edges | Runners out of frame → `NOT_VISIBLE`; pack-space computed over visible subset only; if visible subset < 3, `UNKNOWN` for all (M4 DoD). Suppress `DETACHED` on any longitudinal boundary whose comparison group may be off-frame. | `pct_pack_coherent` |
| EC-03 | DQ / DAI / pulled-up runner (tracklet dies legitimately) | Tracklet ends; runner in official DAI/DQ list or has no finish position | Terminate chart at last confident frame with `terminal_reason`; MUST NOT count toward coverage-gate failure | `terminal_reason` per runner |
| EC-04 | Volte vs. autostart (different `t_0` semantics) | Race metadata `start_type` | Volte: `t_0` = release into racing direction ("depart lancé" moment as clicked); autostart: `t_0` = gate-car pull-away. Tool displays `start_type` and `start_format` (with rendement bands for `volte_handicap`) before anchor capture | `start_type`, `t0_method` |
| EC-05 | Night meetings (Vincennes floodlights; detection-quality shift) | Metadata (meeting time) + luminance stats | In scope from day one (premium program is nocturnal); M2 trained on both strata; all metrics reported per stratum (§6.3) | `stratum ∈ {day, night}` |
| EC-06 | Broadcast graphics occluding the pack (odds banners, lower thirds) | M1 `graphic_overlay_mask_ref` / static-region detector; M7 intersects the mask with supported or coasted runner boxes | Occluded runners → `NOT_VISIBLE`; if > `graphic_occlusion_max` of wide-pan time has ≥ 1 runner footprint intersecting the mask, race `unchartable` | `pct_graphic_occluded` |
| EC-07 | In-broadcast replay segment (slow-mo, alternate angle inside live feed) | M1 `replay_insert` class (visual cues: slow-mo cadence, replay wipe/graphics) | MUST NOT be charted; double-charting a race interval is corpus poisoning (M1 DoD) | `n_replay_inserts` |
| EC-08 | Prolonged occlusion cluster (runner hidden behind another > `occl_max_s`) | Tracker coasting without detection support | Emit `NOT_VISIBLE` after `occl_max_s` (default 1.5 s) of coasting; re-association only via human seed or high-confidence re-match; silent long coasting banned | `occl_events` |
| EC-09 | Tracker ID swap inside occlusion cluster | Contradiction in observed finish-crossing/start-position checks (M3 DoD) or human spot-check | Race flagged `id_suspect`; excluded from golden metrics until re-seeded. An inconclusive consistency check alone is not a failure. | `id_suspect`, `finish_check_status`, `start_check_status` |
| EC-10 | Replay VOD covers race partially (missing start or finish) | M0 duration vs. the official winner's `official_elapsed_norm_s` (heuristic; skipped when NULL); missing anchor frames | If `t_0` or `t_end` unanchorable → `unchartable` (fraction-of-race timeline undefined) | `anchor_missing` |
| EC-11 | Non-partant / late scratch still in metadata | Declared runner never detected + official NP list | Runner excluded from pack-space and coverage denominators | `np_list` |
| EC-12 | Timeline-anchor duration disagrees with the first-past runner's normalized official time | `abs((tend_video_s - t0_video_s) - official_elapsed_norm_s(first_past) - anchor_offset_<start_type>_s) > anchor_tol_<start_type>_s` (per-start-type bias offset and tolerance, D-34; all four keys `[EG: OD-1x]`), where `race_anchors.official_time_method` is resolved in M3 per D-25 and the norm column is the only permitted time source | Tool requests one re-click of the suspect anchor; persistent mismatch → `anchor_check_status = mismatch`, `anchor_suspect = true`, race `unchartable`. `official_time_method = unavailable` or unresolved `first_past_saddle_no` → `anchor_check_status = inconclusive`, not suspect (Q-3 unaffected). Otherwise `pass` | `anchor_check_status`, `anchor_suspect`, `anchor_duration_delta_s` |
| EC-13 | Rail lane empty or rail reference unreliable | Rail-reference confidence below `rail_ref_conf_min`, or innermost occupied-cluster center > `rail_attach_sw` from `rail_ref_w_sw + rail_lane_center_offset_sw` | Preserve relative cluster IDs for diagnostics but emit absolute `tier = NULL`, `conf = 0` and downstream `UNKNOWN`; never promote the innermost occupied cluster to tier 1 | `pct_rail_reference_valid` |
| EC-14 | Faux départ / volte recall (aborted start, restart) | Post-release deceleration or turn-back of the pack; restart footage; commentary cue noted by the operator | `t_0` MUST anchor the **final** release; the tool surfaces a "possible recall" flag and MUST NOT auto-correct; the first release's timecode MAY be logged for diagnostics (DR-03) | `recall_suspected` |

---

## 9. Data Schema (normative shape; columns extensible via minor versions — D-13)

Storage: relational store (SQLite default, §13) + parquet exports. Every table carries `schema_version`, `producer_version` and `created_at`. Every row emitted or mutated as part of a CV pipeline run—including operator-assisted identity, anchor, calibration and review artifacts—additionally requires non-null `extractor_version` and `threshold_set_version`. Standalone human-chart, text-parse and configuration artifacts MAY leave those two fields NULL and use their charting/parser/config build as `producer_version`. Keys below are abridged: every versioned artifact key includes `producer_version` (and CV uniqueness includes its extractor/threshold pair), so coexisting versions never overwrite one another. Agents implement full DDL in M8.

| Table | Key columns | Content |
|-------|------------|---------|
| `races` | `race_id` | Date, meeting, race no., `base_distance_m`, `start_type`, `start_format`, `start_handicap`, `piste ∈ {GP, PP}` (DR-06), `arrival_revised ∈ {true, false, NULL}`, `metadata_conflict_codes` (lex-sorted set), source URI, source/normalized video hashes, fps, width/height and duration metadata |
| `runners` | `race_id, saddle_no` | Driver, horse, post/volte band, `autostart_row ∈ {1, 2, NULL}` (DR-04), `distance_run_m`, `rendement_m`, finish position, nullable `provisional_position`, official status (DAI/DQ/NP), `arrival_revision_type ∈ {none, retrograde, post_finish_dq, other, unknown}`, nullable `official_elapsed_s`, nullable `official_km_rate_s`, `time_normalization_status ∈ {direct_elapsed, km_rate_derived, unavailable}`, nullable `official_elapsed_norm_s`, raw time strings, odds snapshot fields (optional, owner-joined later) |
| `shots` | `race_id, shot_id` | `type`, `t_start_video_s`, `t_end_video_s`, `confidence`, nullable `graphic_overlay_mask_ref` |
| `tracklets` | `race_id, shot_id, tracklet_id` | Frame-indexed boxes (parquet blob/sidecar), tracker params hash |
| `id_assignments` | `race_id, shot_id, tracklet_id` | `saddle_no`, `method`, `human_confirmed`, `seed_frame`, `seed_video_s` |
| `race_anchors` | `race_id` | `t0_frame`, `t0_video_s`, `t0_method`, `tend_frame`, `tend_video_s`, `tend_method`, nullable `first_past_saddle_no`, nullable `first_past_method ∈ {official_unrevised, official_assumed, observed_crossing, human_confirm}`, `finish_evidence_n` (D-30), `recall_suspected` (EC-14), `official_time_method ∈ {direct_elapsed, km_rate_derived, unavailable}`, `anchor_check_status ∈ {pass, mismatch, inconclusive}`, `anchor_duration_delta_s`, `anchor_suspect`, `human_confirmed` |
| `shot_calibrations` | `race_id, shot_id` | `travel_direction_sign`, `rail_side`, per-component heuristic confidence, `method ∈ {heuristic, human_confirm}`, `human_confirmed` |
| `geometry` | `race_id, saddle_no, frame` | `l_sl`, `w_sw`, `rank_long`, `tier_cluster`, nullable absolute `tier`, `order_ambiguous`, `rail_ref_w_sw`, `rail_ref_conf`, `conf` (parquet sidecar; relational store holds pointers) |
| `state_segments` | `race_id, saddle_no, seg_id` | `state_kind`, `state`, `covered`, `lead_uncovered_outside`, `lead_uncovered_outside_ambiguous`, `tier_attr`, `end_attr`, `method`, `t_start_frac`, `t_end_frac`, `confidence`, `visibility`, `start_truncated`, `end_truncated` |
| `events` | `race_id, saddle_no, event_id` | `type`, attributes per §2.5 incl. `positions_lost_basis_n`, `dai_tag ∈ {dai_uncaught_break_expected, dai_gait_other, NULL}`, `method`, `review_status`, `human_confirmed`, `reviewed_at`; race-level `SHOT_GAP` rows use `saddle_no = 0` |
| `qc` | `race_id` | Race-level §M7 fields: `chartable`, failure codes, wide-pan coverage, human-minutes, stratum, `finish_check_status`, `finish_check_basis`, `start_check_status`, `anchor_check_status`, `id_suspect`, `realization` (DR-11 coverage-failure tag), `recall_suspected` (EC-14) |
| `runner_qc` | `race_id, saddle_no` | `pct_time_visible`, `pct_final_third_visible`, `pct_time_stateable`, `pct_final_third_stateable`, `occl_events`, denominator interval, `terminal_reason`, terminal timestamp, `terminal_before_final_third` |
| `threshold_sets` | `threshold_set_version` | Full registry values (§7.1), search provenance |
| `versions` | `producer_version` | `producer_kind ∈ {cv_extract, human_chart, text_parse, config, pilot_throwaway}` (§0.4), `determinism_env` (D-32), nullable `extractor_version`, module/tool git hashes, model weight hashes, date |
| `hand_charts` | `race_id, saddle_no, seg_id` | Same segment payload as `state_segments` + `charter_minutes`; `method = human_chart` (or `text_parse` when §11 activates), method-specific `producer_version`, `split ∈ {dev, heldout}` |

**Invariants:** `schema_version` equals the governing SPEC semver. `state_segments` and `hand_charts` share the same segment payload — the schema is the stable artifact (D-05). On `state_segments`, `events` and `hand_charts`, `method ∈ {cv_extract, human_chart, text_parse}` identifies the filler; table-specific method fields elsewhere retain the enums stated in their own rows/contracts. Operational `created_at` is retained in storage but excluded from the canonical deterministic export (§M8).

Payload constraints: `covered` is boolean for geometric base states and NULL for `NOT_VISIBLE`/`UNKNOWN`. `lead_uncovered_outside` is false on known non-`PARKED` geometric states, boolean on unambiguous `PARKED`, and NULL on `NOT_VISIBLE`, `UNKNOWN` or an ambiguous top-`PARKED` tie. `lead_uncovered_outside_ambiguous` is true only for that tie, false on other known geometric states, and NULL on `NOT_VISIBLE`/`UNKNOWN`. An overlay inherits the co-timed base `visibility` plus all three relational fields and MUST split when an inherited value changes. `tier_attr` is required on `WIDE`; `end_attr ∈ {front, rear}` is required only on `DETACHED`. Exactly one base segment covers each `(race_id, saddle_no, charted timestamp)`; overlay segments MAY overlap it and one another.

**Canonical payload for DoD-5:** M8 MUST emit a hashable UTF-8 JSONL test representation per table in addition to operational SQLite/parquet. Unicode is NFC, line endings are LF, keys follow schema order, rows sort by the full versioned primary key, NULL/booleans use JSON literals, and finite floats are **quantized to fixed decimals before hashing** (race fractions 6 dp; seconds 3 dp; SL/SW/confidence 4 dp) and serialized as decimal strings — exact IEEE-754 hex is dropped from the canonical payload and operational storage is unconstrained; quantization applies to the export only, never inside comparisons or threshold logic (D-32). NaN and infinities are forbidden; unavailable numeric values use NULL. Semantically unordered arrays/sets are lexicographically sorted, while ordered sequences such as `source_shot_types` preserve source order. `created_at`, `reviewed_at`, operator action wall-clock timestamps and `human_minutes` are excluded; clicked video/frame timestamps and review decisions remain included. Binary/parquet sidecars are represented by SHA-256 content hashes. Byte identity and the recorded aggregate SHA-256 are evaluated on this representation, not on SQLite/parquet container bytes.

All non-source artifact IDs MUST also be deterministic. Within the non-ID parent key, assign a content-derived ID or a zero-based ordinal after sorting the canonical record with its ID omitted (NULL sorts last); `shot_id`, `seg_id` and `event_id` use `t_start_video_s`, `t_start_frac` and `t_start_frac` respectively as their leading sort fields. Full canonical record bytes break remaining ties. Random UUIDs and database insertion-order IDs MUST NOT enter the canonical payload. Any stochastic inference component fixes and records its RNG seed and deterministic-runtime settings under `producer_version.determinism_env`: framework/CUDA/cuDNN/driver versions, GPU model and count, `use_deterministic_algorithms`, `cudnn.benchmark`, `cudnn.deterministic`, TF32 flags, `CUBLAS_WORKSPACE_CONFIG`, seed, half-precision flag, batch size, model-weight hashes. Bit-identity across machines is NOT required (D-32); same-environment bit-identity of unquantized sidecars is an optional CI check.

---

## 10. QC Gates (normative)

For QC, a frame is **pack-coherent** iff its base shot is `wide_pan`, it is not a `replay_insert`, and M4 has valid projection for ≥ 3 active non-NP runners (active = before any confirmed EC-03 terminal timestamp). `coverage_race` is pack-coherent duration divided by `[t_0, t_end]` duration. `coverage_final_third` applies the same numerator/denominator rule only to `[2/3, 1]` race fraction. Durations, not frame counts, are used so normalized-fps changes cannot alter the result.

Race-level `chartable = true` requires ALL of:

| Gate | Rule (defaults; config-versioned with §7) |
|------|------------------------------------------|
| Q-1 | Wide-pan pack-coherent coverage ≥ 0.65 of race duration (`coverage_race_min`) |
| Q-2 | Pack-coherent coverage of final third ≥ 0.70 (`coverage_final_third_min`) |
| Q-3 | Both timeline anchors present and not `anchor_suspect` (EC-10/EC-12) |
| Q-4 | Not `id_suspect` (EC-09) |
| Q-5 | Graphic-affected wide-pan time ≤ `graphic_occlusion_max` (EC-06) |
| Q-6 | Field size ≤ 14 (D-06) and discipline = attelé |
| Q-7 | Human budget respected (`human_minutes ≤ human_budget_cap_min`, 8 min `[EG: pilot ≈ p90]`); `over_budget` is not waivable in v1 (D-09, D-29) |

Failure codes are closed in v1: `coverage_race_low`, `coverage_final_third_low`, `anchor_missing`, `anchor_suspect`, `id_suspect`, `graphic_occlusion_high`, `field_too_large`, `wrong_discipline`, `over_budget`. A failed gate MUST append its code; multiple codes MAY coexist.

Per-runner denominators run from `t_0` to `t_end`, except an EC-03 terminal runner, whose denominator ends at its confirmed terminal timestamp. `visible` means a supported runner detection exists (`state != NOT_VISIBLE`); `stateable` additionally requires a known geometric base state (`state ∉ {NOT_VISIBLE, UNKNOWN}`). Non-charted shot time contributes to neither numerator. If the denominator does not intersect the final third, both final-third fractions are NULL with `terminal_before_final_third = true`; they MUST NOT be coerced to zero. Features downstream MUST consume the matching visible **and stateable** fractions alongside any state aggregate; emitting an aggregate without them is a schema violation (D-11).

---

## 11. Lexicon Bridge (normative mapping rules — D-20; OD-2 resolved)

### 11.1 Source and evidence status

This bridge reuses the owner's 2026-05 NLP pattern-discovery work, restricted to **Attelé post-race `notule_runner_texte`**:

- `[C]` = phrase family attested in the 2019-01-01 through 2026-05-23 Attelé rolling corpus / PMI artifacts.
- `[P]` = phrase family also encoded in `parsers_draft/parsers_notule.py`, built from the reviewed keep-list.

Evidence sources: `claude_research/04_nlp_pattern_discovery/review_20260525.md`, `claude_research/04_nlp_pattern_discovery/parsers_draft/parsers_notule.py`, and `claude_research/04_nlp_pattern_discovery/com_notules_20260524/20260524/03_pmi_notule_rolling/pmi_notule_runner_Attel_y_win.csv`.

`expected_signals.md` is an expectation prior, not evidence. Predictive PMI sign/lift MUST NOT be used as semantic mapping confidence: common trip phrases can be semantically decisive while carrying little predictive lift. Inflected gender/number and ordinary tense variants of an attested lemma are included in the same phrase family.

A mapping rule MAY require a conjunction of separately attested `[C]` families. In that case `[C]` asserts corpus support for the constituent families, not that their combined surface phrase was itself observed; the conjunction remains a semantic rule that must be validated when text parsing is activated.

### 11.2 Vocabulary map

The left-hand state/overlay/event ontology is closed by §§2.3–2.5. The vocabulary column is extensible under the rules in §11.3.

| CV state / overlay / event | French comment vocabulary (owner's lexicon) | Mapping notes / ambiguity flags |
|------------------|--------------------------------------------|---------------------------------|
| `LEADER` | `[C]` « en tête »; « au commandement »; « aux commandes »; « pris / prendre la tête »; « venu(e) / installé(e) / rabattu(e) en tête » | Direct only when the phrase's subject is the runner. « groupe de tête », « tête du wagon » and plural « animateurs » express proximity, not sole leadership. |
| `POCKET` | `[C]` « dans le dos de l'animateur / l'animatrice »; « dans le sillage de l'animateur / l'animatrice »; « dos du leader » | These phrases establish cover behind the leader, but not rail placement by themselves. Emit `POCKET` only with explicit rail/first-trailing-position evidence; otherwise the candidate set is `{POCKET, OUTSIDE_COVERED}` and no exact CV state is emitted. |
| `RAIL_COVERED` | `[C]` « sur une deuxième / troisième / quatrième / cinquième ligne à la corde »; « ligne / rang côté corde »; « peloton côté corde »; « le long de la corde » | « deuxième ligne à la corde » or leader-back language can resolve to `POCKET`; deeper numbered rail lines resolve to `RAIL_COVERED`. Bare « à la corde » proves rail placement only, not cover or depth. |
| `RAIL_UNCOVERED` | `[C]` conjunction of « sans dos » with « à la corde / côté corde » | Both rail placement and absence of cover must be explicit. Bare « à la corde » remains unresolved; bare « sans dos » may instead be `PARKED`. |
| `OUTSIDE_COVERED` | `[C]` « dans un dos »; « dans / prendre / profiter du sillage »; « à l'abri »; « progressé / rapproché(e) à l'abri »; « ramené(e) par »; « wagon de l'extérieur » | Cover and outside tier must both be explicit. « dans un dos », « sillage » or « à l'abri » without « en dehors », « deuxième épaisseur » or « wagon de l'extérieur » remains ambiguous with rail-covered states. |
| `PARKED` / `lead_uncovered_outside` | `[C]` « nez au vent »; « en deuxième épaisseur, le nez au vent »; « s'est retrouvé(e) nez au vent »; « sans dos »; « dehors / côté de l'animateur »; « à hauteur de l'animateur / l'animatrice » | « nez au vent » establishes no cover but still needs non-leader/outside context for `PARKED`. `lead_uncovered_outside = true` (positional sense, §2.3 — not the move-detection event) additionally requires explicit proximity to the leader, e.g. « à hauteur / côté / dehors de l'animateur ». « en deuxième épaisseur » alone does not prove no cover; « parcours difficile » is an assessment, not a state. |
| `WIDE` | `[C]` « en troisième épaisseur »; « en quatrième épaisseur »; « tout en dehors »; « au large » | Numbered third/fourth thickness is direct tier evidence. « en épaisseur » or « en dehors » without a number may be tier 2 and MUST NOT be upgraded to `WIDE`. « largement » is unrelated. |
| `DETACHED` overlay | `[C]` « détaché(e) »; « s'est détaché(e) »; « en net / très net retrait »; « loin du groupe »; « dans le lointain »; « attardé(e) »; « décroché(e) » | « détaché(e) » needs context to set `end ∈ {front, rear}`. « en queue de peloton » and bare « en retrait » describe rank, not necessarily a gap above `detach_sl`; require a gap intensifier or explicit separation. |
| `BREAK` + `recovered` attribute | `[P][C]` « s'est enlevé(e) »; « a fait / commis une faute »; « sur une faute »; « faute au départ / tournant / entrée de la ligne droite »; « après sa faute »; « remis(e) / repris(e) au trot »; « a perdu du terrain sur une faute »; « a été disqualifié(e) » | A break mention creates a `BREAK` candidate. `recovered = true` requires explicit resumption (`remis/repris au trot`) or an unambiguous subsequent race action after the fault; « après sa faute » alone does not prove recovery. DAI/disqualification is an official outcome, not a recovery flag and not proof of a break unless the text also states one. |
| `STRETCH_BLOCK` (v1.5) | `[C]` « bloqué(e) »; « enfermé(e) »; « gêné(e) »; « n'a / n'a jamais pu s'exprimer »; « a tardé à pouvoir s'exprimer »; « n'a pu se dégager »; « chercher / trouver l'ouverture »; « voir / trouver le jour »; « n'a pas eu le passage » | Requires late/stretch phase plus denied or delayed running room. « gêné(e) » may instead be interference; « trouvé l'ouverture / vu le jour » implies a preceding block but does not supply exact start time. Reserved until v1.5 per §12. |

There is no text mapping for `NOT_VISIBLE`, `UNKNOWN`, `LOW_CONF` or `SHOT_GAP`; these are extractor/QC-only labels.

### 11.3 Text-to-chart rules

1. A lexical hit is **evidence for a candidate**, not authority to relax the geometric definitions in §2.3. Every dimension required by a CV state (rail/outside tier, cover, relative depth) MUST be explicit or the exact state remains unresolved.
2. The parser MUST bind the phrase to the charted runner and resolve negation, comparison, quotation and third-party scope. A phrase describing another runner MUST NOT be copied to the subject.
3. One phrase MAY map to multiple CV states. Ambiguity MUST be preserved as a candidate set or unmapped evidence; the parser MUST NOT choose the most likely state.
4. Text-parsed charts use `method = text_parse`, nullable `t_start_frac` / `t_end_frac`, and `phase ∈ {early, mid, late, stretch, unknown}`. Text-only `stretch` is a semantic subphase of `late`, not an exact fractional bin, and MUST NOT be converted to one without new calibration. Parsers MUST NOT fabricate exact fractions from sentence order. Activating text parsing requires the schema-additive `phase`, `source_text_id`, `source_phrase`, `mapping_rule_version`, `mapping_confidence`, `mapping_status` and nullable `candidate_states` columns (minor version).
5. Mapping confidence measures semantic specificity and subject/phase certainty only. It MUST NOT incorporate PMI, lift, the downstream target, or phrase frequency.
6. Same-race text may fill that race's chart only as a post-race artifact. Predictive features for a target race MUST consume charts/comments from strictly prior races; the existing rolling-history leakage guard remains in force.
7. NLP families for finish quality, acceleration, decisive wins, fading, equipment/conditions and jury relegation are **not trip-state mappings**. In particular, « rapidement faibli », « complètement cédé » or « largement dominé » MUST NOT become `DETACHED` without explicit separation, and `rétrogradé/déclassé après enquête` MUST NOT become `BREAK`. Relegation text is supporting evidence for `arrival_revision_type` during M3 adjudication only; it is never authoritative official status (D-23).
8. Text-derived `BREAK` events enter with `review_status = pending` and `human_confirmed = false` until reviewed under the M3/M6 confirmation loop. Phase-level text charts MUST be evaluated separately from exact-fraction CV charts.

### 11.4 Phase vocabulary (shape normative; entries `[C]`-gated — DR-08)

Phase phrases map to `phase ∈ {early, mid, late, stretch, unknown}` under the same `[C]` evidence rules as states (§11.1). Entries below are the attested families to be confirmed with corpus provenance before text parsing activates; unattested entries MUST NOT be used.

| Phrase family | Phase | Notes |
|---|---|---|
| « dès le départ », « au départ », « dans les premiers mètres » | early | — |
| « à mi-parcours », « à mi-course » | mid | — |
| « dans le dernier tournant », « à l'entrée de la ligne droite », « dans la montée » | late | « la montée » is Vincennes-specific (grande piste) |
| « dans la ligne droite », « sur le poteau », « au poteau » | stretch | semantic subphase of late; never converted to a fraction |
| « en fin de course », « sur la fin » | late | ambiguous late/stretch → `late` |

---

## 12. Out-of-Scope Register & Roadmap (normative)

| Item | Status | Earliest re-entry |
|------|--------|-------------------|
| Stretch-block event (`STRETCH_BLOCK`) | Deferred | v1.5 (requires head-on shot context or fine lateral clearance) |
| Head-on / alternate shot extraction contexts | Deferred | v1.5+ (as independent context, still no stitching) |
| Cross-shot identity stitching | Banned | ≥ v3 |
| Fully automatic identity (OCR saddle numbers / silk re-ID) | Banned | ≥ v2, trained on accumulated seeding clicks |
| Whip, head carriage, driver gaze, fatigue/pose signals | Banned | ≥ v3 |
| Metric ground-loss / homography to track coordinates | Banned | Only if GPS/sectional data materializes as calibration source |
| Monté discipline | Excluded | Separate spec (different gait dynamics, break signatures) |
| Tracks other than Vincennes | Excluded | v2 (per-track shot assumptions must be re-validated) |
| Fields > 14 runners | Excluded | v2 (occlusion load) |
| Predictive modeling / feature engineering on charts | Out of project boundary | Separate project; consumes §9 exports |
| Text-comment parsing into the schema | Out of this spec's build | Parallel workstream; writes `hand_charts`-shaped data per §11 rules |
| Detached groups (breakaway pairs) | Deferred | v1.5 (D-28) |
| Move-detection "first over" event (the horse that first leaves cover to advance) | Deferred | v1.5 (S-1; `lead_uncovered_outside` is positional) |
| Official per-runner tracking data as a source | To evaluate before the pilot | could supersede M2–M4 for rank/position (RP-6) |
| Pose-based gait classification for breaks | Deferred | v1.5 (RP-16; needs tight-shot resolution) |
| Track-landmark / phase-topology detection | Banned | reconstruct downstream from `piste` + distance + RK (DR-07) |

---

## 13. Default Stack (NON-NORMATIVE — D-15; replaceable if §4 contracts and tests pass)

| Concern | Pinned default |
|---------|----------------|
| Language / runtime | Python ≥ 3.11 |
| Detection | Ultralytics YOLO family (v8/v11), single class, fine-tuned on owner annotations |
| Tracking | ByteTrack or BoT-SORT (as shipped with Ultralytics), coasting limits per EC-08 |
| Shot segmentation | PySceneDetect (cuts) + small CNN/CLIP-linear frame classifier (base shot type) + static overlay-mask detector for broadcast graphics |
| Geometry / video | OpenCV, ffmpeg |
| Seeding tool | OpenCV window + keyboard handler (no web UI in v1, D-16) |
| Storage | SQLite (relational) + parquet sidecars (frame-level series); pandas/polars for exports |
| Config | Single YAML per `threshold_set_version`, committed to repo |
| Experiment tracking | Plain changelog entries in this file + `versions` table (no MLOps platform in v1) |

Annotation for M2 training: keyframe labeling with interpolation (CVAT or Roboflow acceptable; artifacts exported to repo-owned formats so the platform is not a dependency).

---

## 14. Governance, Versioning & Changelog (normative)

- **Semver:** MAJOR = breaking schema/state-taxonomy change; MINOR = additive (new EC entries, new columns, new modules); PATCH = editorial.
- Decision log (§1) is append-only; reopening a decision = MAJOR bump + owner sign-off.
- Every held-out evaluation appends a changelog entry with versions + headline score.
- This file is the single source of truth; build prompts for coding agents MUST reference a specific spec version.

### Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-07-25 | Initial frozen spec from decision drills D-01…D-21 and same-day coherence review. Completed OD-2/§11; made base states exhaustive; moved `DETACHED` to an overlay; fixed ordering/rail anchoring, event review + `SHOT_GAP` contracts, held-out abstention guards, metrics, budget/QC persistence, runner QC, graphics masking and deterministic exports. Open: OD-1 (sample replays), OD-3 (hand charts). |
| 1.1.0 | 2026-07-25 | Domain drill fixes DR-01/DR-05/DR-02 (D-22…D-24). Rendements: per-runner `distance_run_m`/`rendement_m`, `start_format` invariants, band-based volte start check, DETACHED interpretation note, start-format golden strata + OD-1 coverage. First past the post: `t_end` referent pinned, crossing-order finish check with revision carve-out and human adjudication, `first_past_saddle_no`/`first_past_method`, revision fields on races/runners, `finish_check_basis`. Time normalization: per-runner `official_elapsed_s`/`official_km_rate_s` with unit-provenance and consistency guards, `official_time_method`, EC-12 re-referenced to first-past runner with tri-state `anchor_check_status`. Additive schema + 3 new threshold keys; no artifact migration (none exist under 1.0.0). Open: OD-1, OD-3. |
| 2.0.0-draft | 2026-11-04 | DRAFT cut from 1.2.0 per RECON-2.0.0 and `RECON-2.0.0-patches.md` (edit ledger L-01…L-45; `tools/cut_draft.py`). Cover tier-independent with span-bounded tiers (D-26); headline re-cut to the uncovered-outside mask, `first_over` → `lead_uncovered_outside` (D-27); DETACHED diagnostic-only (D-28); cap/target split, ≥ 2× playback (D-29); `official_assumed` evidence bar (D-30); statistical honesty package (D-31); quantized canonical export (D-32); kill-gates + pilot exemption (D-33); per-start-type anchor offsets/tolerances (D-34); per-stratum yield, dual headline reporting (D-35); DRAFT-until-evidence (D-36). New: `piste`, `autostart_row`, EC-14, §11.4, S-3/S-5/S-6 fixes, DR-10 rule. Open: OD-1x, OD-3, OD-4, RP-11, signal gate. No artifact migration (none exist under 1.x). |
| 1.2.0 | 2026-07-25 | Post-corpus-verification corrections (90,451-row Equidia check), D-25/OD-4. Sequencing: per-runner `time_normalization_status` + `official_elapsed_norm_s` computed in M0; race-level `official_time_method` resolved in M3 and moved from `races` to `race_anchors` (day-old column, zero consumers — defect correction, not a reopened decision). Ambiguity fix: EC-10/EC-12 consume `official_elapsed_norm_s` only. `time_unit_consistency_tol_s` 2.0 → 0.5 (corpus max direct-vs-derived delta 0.205 s; one 25 m band ≈ 1.8–1.9 s), making the check a distance-band validator; malformed-row fixture added. Metadata-poor first-past: `official_assumed` mode with reconstruction corroboration, `final_assumed` basis, reference order includes `unknown`-status runners, `arrival_revised` never defaulted to false. Open: OD-1, OD-3, OD-4. |

---

## Annex A — Extended Rationale (informative)

- **Why topological states, not metrics (D-03/D-07):** A panning, zooming broadcast destroys pixel↔meter stability; camera motion dominates pixel-path integrals. Ordering, tiering, and cover are invariant to zoom and pan because they are relations *within* the pack, and they coincide with the canonical harness-racing trip variables (first-over, pocket, covered) that decades of standardbred handicapping identify as performance-relevant and that French commercial data does not carry.
- **Why human-in-the-loop identity (D-01):** Anonymous tracklets make every downstream feature per-blob, not per-horse. OCR of saddle cloths at broadcast resolution through occlusion is the hardest CV sub-problem in the pipeline; deferring it converts a research risk into a bounded 5-min/race operating cost while accumulating exactly the labels needed to attack it later.
- **Why coverage gates are non-negotiable (D-11):** Director cuts are correlated with race action (they cut away from the mid-pack when the leaders duel), so missing coverage is *not* missing-at-random; uncorrected, it biases parked/blocked durations in exactly the races where they matter most.
- **Why the schema is the artifact (D-05/D-13):** Three fillers (CV, human, text) writing one structure means predictive validation can begin on human/text charts before CV matures, and CV accuracy is measurable as agreement with humans in the same currency.
- **Why rendements are metadata, not geometry corrections (D-22):** The extractor records what the camera shows. A 50 m back-marker producing rear `DETACHED` at `t_0` is a true geometric state whose cause is class, not weakness; suppressing or shifting it would make the chart lie to stay convenient. `rendement_m` lets downstream condition the pattern out — and the same metadata explains why early `rank_long` is class-inverted in `volte_handicap` races, which is interpretation, not extraction.
- **Why `t_end` means first past the post (D-23):** The timeline anchor is a property of the footage; stewards' revisions reorder the official result, not the video. Comparing observed crossings against post-enquête order would manufacture false `id_suspect` in precisely the races with incident drama — the carve-out keeps the identity check about identity, and the anchor stays clickable without knowing the eventual official winner.
- **Why time normalization is paranoid (D-24):** French trot publishes the réduction kilométrique as the headline "time"; a rate mistaken for a duration fails EC-12 on every race while looking like QC working as intended — the definition of silent corruption. Cross-checking elapsed against RK × distance-run also catches the mislabeled-RK case at ingest instead of at calibration, and ties the check to the runner whose crossing actually defines `t_end` (a back-mark winner runs farther than the base distance).

- **Why `official_assumed` beats defaulting `arrival_revised = false` (D-25):** With no authoritative revision field in the ingest, defaulting to "unrevised" is a guess dressed as metadata — wrong in exactly the stewards'-drama races where the finish check matters. The crossing reconstruction M3 must run anyway is a free corroborator: adopting the official winner only when nothing observed contradicts it preserves the zero-click path for ordinary races while routing every anomaly to adjudication instead of silently trusting a default.

- **Why cover is geometric and the headline is a mask (D-26/D-27):** the energetic toll is being outside *and* uncovered, independent of which lane; a cover definition that inherits tier clustering flips at an arbitrary boundary, and a headline on the `PARKED` label excludes the three-wide uncovered case it exists to measure. Labels stay categorical for the lexicon; the money metric follows the physics.
- **Why `official_assumed` needs observed crossings (D-30):** D-25's defence rests on the reconstruction being a free corroborator; with zero observed crossings it corroborates nothing and adoption becomes the "guess dressed as metadata" D-25 forbids.
- **Why the field-size cap is a known bias (DR-11):** the ≤ 14 cap and cinematic big-race realizations exclude the deepest betting pools by construction; the exclusion is missing-not-at-random and accepted for v1, and `qc.realization` makes it quantifiable rather than invisible.
- **Why lateral scale is suspect (RP-5):** SW is derived from SL under an implicit fixed-yaw assumption; an oblique wide pan compresses lateral distances relative to longitudinal ones, and bends add axis error. OD-1x step 4 measures it; the fix, if needed, is a scale aid, not a homography.

*End of SPEC-2.0.0-draft.*
