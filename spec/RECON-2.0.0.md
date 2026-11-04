# RECON-2.0.0 — Full Reconciliation: SPEC-1.2.0 × Review × Remaining Drill Queue

**Status:** Informative planning document. Nothing here is normative; it defines the exact content of SPEC-2.0.0-draft and the evidence protocol that freezes it.
**Inputs reconciled:** SPEC-1.0.0 → 1.2.0 (D-01…D-25, OD-1…OD-4), `spec\_review\_1\_2\_0.md` (B-1…B-4, F-1…F-8, S-1…S-8, §1.3, §6), drill queue DR-03/04/06–12 (open since the DR-01/02/05 round).
**Date:** 2026-07-26

\---

## 1\. Adjudication — every open item, one verdict each

Legend: **\[now]** = evidence-independent, lands verbatim in 2.0.0-draft. **\[EG]** = structure lands in draft, numeric value instantiated only by OD-1x data. **\[reg]** = out-of-scope register entry with re-entry version.

|Item|Verdict|Resolution|Decision|Gate|
|-|-|-|-|-|
|§1.3 anchor tolerance unverified|**Accept, extend**|Split into per-start-type **bias + tolerance** pairs (`anchor\_offset\_{volte,autostart}\_s`, `anchor\_tol\_{volte,autostart}\_s`). Systematic click bias gets *corrected* by the offset, not swallowed by a fat tolerance — same philosophy as D-24. Defaults provisional.|D-34|EG|
|B-1 seeding feasibility untested|**Accept**|OD-1 → **OD-1x**: timed seeding dry run is the core, shot survey is the side effect. Protocol in §5.|D-33/D-34|EG|
|B-2 DoD-3 = Q-7 bisects distribution|**Accept, choose values**|Q-7 cap → **8 min** (tail truncator); DoD-3 median target stays **≤ 5 min** (owner intent preserved). Structural rule: cap ≥ 1.5 × median target, re-instantiated at ≈ p90 of pilot distribution. `over\_budget` stays non-waivable.|D-29|EG (values) / now (structure)|
|B-3 no yield floor, MNAR yield|**Accept**|Per-stratum `chartable` rate added to §6.2/M7 reporting (strata: day/night × field-size band × `start\_format` × `piste`). Review trigger: any stratum yield < 0.5 × overall → manifest/threshold review before further charting. No hard floor pre-data; pilot yield joins the kill-gates.|D-35|now (instrument) / EG (trigger values)|
|B-4 `official\_assumed` vacuous corroboration|**Accept — 1.2.0 defect, mine**|Rung (ii) requires ≥ `finish\_evidence\_min\_k` observed crossings (default 3, registry key), all consistent with the reference order. Zero/insufficient observations → `first\_past\_saddle\_no = NULL`, EC-12 `inconclusive`. Relegation fixture unchanged; new fixture: head-on finish, zero observed crossings → NULL, never `official\_assumed`.|D-30|now|
|F-1 cover coupled to tier clustering|**Accept — strongest structural finding**|Cover becomes a tier-independent geometric predicate: `covered(X) ⇔ ∃Y valid: (l\_Y − l\_X) ∈ \[cover\_min\_sl, cover\_max\_sl] ∧|w\_X − w\_Y|< cover\_lat\_sw`. Tier remains for state \*labels\* only. Existing min-duration smoothing applies to the predicate. `cover\_lat\_sw` default 0.8 SW, eyeballed in OD-1x.|
|F-2 PARKED headline measures a label, not the physics|**Accept**|Headline money component becomes **uncovered-outside mask** IoU: `tier ≥ 2 ∧ covered = false`. D-17 weights re-cut: 0.5 uncovered-outside mask / 0.3 covered mask / 0.2 rest. `PARKED`/`WIDE` labels and §11 mappings unchanged; `tier\_attr` + `covered` in the payload preserve the exact-label view. Reopens D-17 → part of the MAJOR justification.|D-27|now|
|F-3 DETACHED booby-traps the evaluation|**Accept both safeties**|(a) `DETACHED` dropped from headline `rest`; reported descriptively per stratum. (b) Empty-union invalidation scoped to DoD-1 components only. `detach\_sl = 6.0` unchanged — the overlay is *supposed* to be rare. Detached **groups** (breakaway pairs) → out-of-scope register, re-entry v1.5.|D-28|now / reg|
|F-4 DoD-2 untestable at n = 10|**Accept restatement, reject n ≥ 25**|DoD-2 restated: point estimate ≥ 0.80 with Wilson 95% CI **reported**, no certification claim. Raising held-out break minimum to 25 ≈ triples held-out charting cost pre-pilot — unjustifiable; revisit when the corpus grows past golden.|D-31|now|
|F-5 identity audit over-confident|**Accept**|Timestamps stratified across 4 phase bins of `\[t\_0, t\_end]`; runners resampled per timestamp; sampled points MUST touch ≥ 8 distinct tracklet intervals or the audit reports its effective n. Operating characteristic stated in §6.4: accepts ≥ 0.99 per-sample accuracy w.p. ≈ 0.95; a 0.95-accuracy race passes ≈ 0.44 — the audit is a smoke test, not a certificate.|D-31|now|
|F-6 DoD-5 fails across machines|**Accept (b)**|Canonical export quantizes floats to fixed decimals before hashing (SW/SL/conf: 4 dp; seconds: 3 dp); exact hex dropped from the canonical payload (operational storage unconstrained). Determinism env knobs (`use\_deterministic\_algorithms`, cudnn.benchmark, TF32, driver, weights hash) recorded under `producer\_version`; strict same-environment bit-identity demoted to an optional CI check. Quantization applies to the export only — never inside comparisons or threshold logic.|D-32|now|
|F-7 `positions\_lost` can report a gain|**Accept strict form**|Valid only when the visible-runner set is **identical** at both samples; else NULL. `positions\_lost\_basis\_n` recorded.|D-31|now|
|F-8 Q-7 excluded from accuracy voiding|**Accept**|Intent sentence in §6.3 (extractor accuracy ≠ operational yield — deliberate); headline reported both with and without Q-7 failures.|D-35|now|
|S-1 `first\_over` misnamed|**Accept rename**|→ `lead\_uncovered\_outside` (attribute + §11.2 mapping, positional sense documented). Event-sense "first over" (move detection) → out-of-scope register, v1.5. Breaking rename → MAJOR justification.|D-27|now|
|S-2 phases vs per-runner distance|**Accept**|One normative sentence in §2.6: `t\_frac` is race-clock fraction, not per-runner course fraction; downstream conditions on `base\_distance\_m`/`distance\_run\_m`/`piste`. Merges with DR-07.|D-22 note|now|
|S-3 M0 branch-4 status unnamed|**Accept**|Elapsed-only + plausible → `direct\_elapsed`; km-rate-only + plausible → `km\_rate\_derived`. Explicit in rule 4.|—|now|
|S-4 tier-1 span unbounded|**Accept, with deterministic remedy**|`max\_tier\_span\_sw` (default 1.2). Cluster exceeding it splits recursively at its largest internal gap (deterministic). Unit test: 14 runners evenly spread.|D-26|now / EG (value sanity)|
|S-5 `plausible\_km\_rate\_min\_s = 55` inert|**Accept**|→ **65** (attelé record RK ≈ 69 s/km; 65 leaves margin and can actually fire).|—|now|
|S-6 two sources of truth for `split`|**Accept**|§6.1 manifest authoritative; `hand\_charts.split` is a denormalized copy validated at write time; mismatch → write rejected.|—|now|
|S-7 no abort criteria|**Accept**|New §0.4 kill-gates (§8 below).|D-33|now (structure) / EG (values)|
|S-8 FROZEN eroded|**Accept, formalize**|Versioning strategy in §2 below: 1.x closes; 2.0.0-**draft** (DRAFT status); one freeze event, post-evidence.|D-36|now|
|DR-03 faux départ|**Fold in**|New EC-14: volte recall detection (post-release deceleration/turn-back, restart footage); `t\_0` MUST anchor the **final** release; tool surfaces a "possible recall" flag.|—|now|
|DR-04 autostart second row|**Fold in**|M3 start check models two rows for fields > 9: front-row lateral order = post order; second row checked for presence only, never order. `runners` gains `autostart\_row ∈ {1, 2, NULL}`.|—|now|
|DR-06 piste not recorded|**Fold in**|`races.piste ∈ {GP, PP}` from ingest (never inferred from distance). Joins B-3 strata and §6.1 manifest stratification. OD-1x samples SHOULD cover the pistes present in the owner's betting corpus.|—|now|
|DR-07 topology vs fraction phases|**Fold in**|Design-intent sentence (with S-2): landmark detection stays banned; approximate track position is reconstructible downstream from `piste` + distance + RK.|—|now|
|DR-08 no phase-vocab table|**Fold in**|§11.4: attested vocab→phase map (« dès le départ », « à mi-parcours », « dans le dernier tournant », « à l'entrée de la ligne droite », « dans la montée », « sur le poteau », …) under the same \[C]-evidence rules as states.|—|now|
|DR-09 amble/traquenard blind spot|**Fold in**|`dai\_uncaught` splits: `dai\_uncaught\_break\_expected` vs `dai\_gait\_other` (human tag at review). §7 calibration MUST NOT tune break thresholds against `dai\_gait\_other`.|—|now|
|DR-10 faute sur le poteau|**Fold in**|Clarification: a break open at `t\_frac = 1.0` → `t\_end\_frac = NULL`, `recovered = NULL`; expected to coincide with DAI; agents MUST NOT "fix" it.|—|now|
|DR-11 field-size cap vs quinté pools|**Fold in (acknowledge)**|Annex A: selection-bias paragraph (≤ 14 cap + cinematic big-race realizations exclude the deepest pools; MNAR by construction, accepted for v1). `qc` gains a `realization` coverage-failure tag so the exclusion is quantifiable. > 14 fields → register, v2 re-entry.|—|now / reg|
|DR-12 marathon budget arithmetic|**Fold in**|Tool DoD: configurable ≥ 2× auto-play with auto-slowdown at flagged events. Complements D-29; removes the distance-correlated corpus hole.|D-29|now|

Previously closed and **not reopened**: D-03 (stretch-block, v1.5), D-01 (no OCR/re-ID — B-1 tests the human side of it, doesn't reopen it), D-08/D-10 semantics except where a decision above explicitly supersedes.

\---

## 2\. Version strategy (resolves S-8 and the freeze-erosion critique)

1. **The 1.x line closes at 1.2.0.** No further 1.x bumps; 1.2.0 remains the last FROZEN metadata-complete spec and the diff base.
2. **Next artifact: SPEC-2.0.0-draft, Status: DRAFT.** MAJOR is honest, not inflationary: D-17 is reopened (headline metric re-cut), a D-08-frozen core definition changes (cover), and a payload field is renamed (`first\_over`). DRAFT means: agents MAY build M0, schema migrations, and tooling scaffolds against it; golden charting and calibration MUST NOT begin.
3. **Every EG value carries an explicit `\[EG: OD-1x]` marker in the draft** with its provisional default and its instantiation rule (§4). Un-instantiated EG markers block the freeze mechanically — the draft cannot be promoted with a marker still present.
4. **One freeze event.** OD-1x closes → EG registry instantiated → kill-gates pass → 2.0.0-draft promotes to 2.0.0 FROZEN in a single commit that also appends D-26…D-36 to the decision log. After that, FROZEN means what it says.

\---

## 3\. Decision allocations (appended at freeze)

|ID|Decision|Rationale|
|-|-|-|
|D-26|Cover is a tier-independent geometric predicate (`cover\_lat\_sw`, `cover\_min\_sl`, `cover\_max\_sl`); tiers label states, geometry decides cover. Tier clusters are span-bounded (`max\_tier\_span\_sw`) with deterministic largest-gap splitting.|The money metric must not inherit clustering artifacts.|
|D-27|Headline money component = uncovered-outside mask IoU (`tier ≥ 2 ∧ ¬covered`), weights 0.5/0.3/0.2; `first\_over` → `lead\_uncovered\_outside` (positional sense).|Measure the physics, not the label boundary.|
|D-28|`DETACHED` is diagnostic-only: excluded from headline `rest`; empty-union invalidation scoped to DoD-1 components.|A deliberately rare overlay must not be able to invalidate an evaluation.|
|D-29|Budget cap ≠ budget target: Q-7 cap 8 min (≈ p90 of pilot at re-instantiation), DoD-3 median ≤ 5 min; seeding tool provides ≥ 2× playback with event slowdown.|A hard cap truncates a tail; it must not bisect the distribution.|
|D-30|`official\_assumed` requires ≥ `finish\_evidence\_min\_k` observed crossings consistent with the reference; zero-evidence adoption is forbidden.|A corroborator with no observations is not a corroborator.|
|D-31|Statistical honesty package: DoD-2 as point estimate + reported CI; §6.4 stratified sampling with stated operating characteristic; `positions\_lost` requires an identical visible set.|The spec refuses to overclaim elsewhere; metrics must too.|
|D-32|Cross-machine determinism via fixed-decimal canonical quantization; environment knobs pinned and recorded; bit-exact hex demoted to optional same-env CI.|The strictest representation must not be paired with the least reproducible producer.|
|D-33|Kill-gates (§0.4): the project defines when to stop, not only when it is done.|Cheap insurance against sunk cost; extends D-09's posture to the project level.|
|D-34|Anchor QC uses per-start-type bias offsets + tolerances, measured before frozen; unverified tolerances are treated like unverified units.|The D-24 failure mode, one tolerance over.|
|D-35|Yield is instrumented per stratum with a differential-yield review trigger; headline accuracy reported with and without Q-7 failures.|Gate outcomes are MNAR for the same reason coverage is.|
|D-36|DRAFT-until-evidence: EG markers block promotion; one freeze event per major line.|FROZEN is a load-bearing word.|

\---

## 4\. Evidence-gated registry (instantiated by OD-1x, blocks the freeze)

|Key|Provisional|Instrument|Instantiation rule|
|-|-|-|-|
|`anchor\_offset\_volte\_s` / `anchor\_offset\_autostart\_s`|0.0 / 0.0|3 repeated `t\_0`+`t\_end` clicks per replay vs official elapsed|offset := median signed bias per start type|
|`anchor\_tol\_volte\_s` / `anchor\_tol\_autostart\_s`|2.0 / 2.0|same|tol := max(0.5, \~p95 of|
|`cover\_lat\_sw`|0.8|frame eyeball on 14-runner fields|adjusted so real off-the-wheel cover positions classify as covered|
|`same\_tier\_sw` / `max\_tier\_span\_sw` sanity|0.6 / 1.2|same frames|confirm lateral separations resolve; else recalibrate before M4 work|
|Q-1 / Q-2 coverage gates|0.65 / 0.70|% wide-pan of `\[t\_0, t\_end]` and of final third|confirm real replays clear the gates; else gates or corpus definition revisited **before** charting|
|Q-7 cap / DoD-3 target|8 / 5 min|timed seeding dry run + 5-race pilot|cap := \~p90 pilot; target := pilot median rounded up|
|`finish\_evidence\_min\_k`|3|finish-shot crossing counts on the samples|lower only if typical finish shots observe < 3 crossings *and* order remains unambiguous|
|`detach\_sl` prevalence check|6.0 (unchanged)|count 6.0 SL gaps in samples|no change expected; confirms D-28's rarity premise|

\---

## 5\. OD-1x protocol (supersedes OD-1; one afternoon)

Samples: three replays per D-22 stratification (one autostart, one flat volte, one handicap volte); cover the pistes present in the betting corpus where possible (DR-06).

1. **Timed seeding.** Seconds to assign all saddle numbers from the first stable wide-pan frame, per race, full field. Falsifies/confirms D-01's human premise, B-1, B-2, DoD-3.
2. **Anchor reproducibility + bias.** 3× `t\_0` and `t\_end` clicks per replay; signed residual vs normalized official elapsed, split by start type. Instantiates D-34 keys; tests EC-12.
3. **Coverage.** % wide-pan over `\[t\_0, t\_end]` and over the final third. Tests Q-1/Q-2; first real input to B-3.
4. **Geometry eyeball.** Lateral separations at 14 runners vs `same\_tier\_sw`/`cover\_lat\_sw`; occurrence of ≥ 6 SL gaps. First evidence on F-1/F-3 parameters.
5. **Finish-shot evidence.** Observed-crossing counts and identifiability → `finish\_evidence\_min\_k` feasibility (D-30).
6. **Recall/faux-départ scan.** Note any aborted starts in the footage → EC-14 heuristic sanity (DR-03).

\---

## 6\. SPEC-2.0.0-draft content plan (delta over 1.2.0, by section)

* **Header/§14:** version 2.0.0-draft, Status DRAFT, D-36 promotion rule; changelog entry.
* **§0.2:** DoD-2 restated (D-31); DoD-3/Q-7 split (D-29); DoD-5 quantized-canonical semantics (D-32).
* **§0.3:** OD-1 → OD-1x (protocol §5); OD-4 unchanged.
* **New §0.4:** kill-gates (§8 below).
* **§1:** D-26…D-36 appended at freeze.
* **§2.2:** cover predicate (D-26); `max\_tier\_span\_sw` + largest-gap splitting; unit test.
* **§2.3:** `first\_over` → `lead\_uncovered\_outside`; labels otherwise unchanged.
* **§2.4:** DETACHED unchanged except D-28 cross-reference; detached-groups register entry.
* **§2.5:** `positions\_lost` identical-visible-set rule + `positions\_lost\_basis\_n`; DR-10 wire-break clarification.
* **§2.6:** S-2/DR-07 race-clock sentence.
* **§4 M0:** S-3 branch statuses; `plausible\_km\_rate\_min\_s = 65`; `races.piste`; `runners.autostart\_row`.
* **§4 M3:** D-30 evidence bar + zero-crossing fixture; DR-04 two-row start check; anchor offset/tol keys in EC-12 comparison.
* **§4 M6:** `dai\_uncaught` split (DR-09); calibration guard.
* **§5.1:** ≥ 2× playback tool DoD (DR-12); Q-7 = 8 min.
* **§6.1:** manifest authoritative for `split` (S-6); strata gain `piste`.
* **§6.2:** headline re-cut (D-27); DETACHED out of `rest` (D-28); per-stratum `chartable` rate (D-35).
* **§6.3:** F-8 intent sentence + dual headline reporting; DoD-2 CI reporting.
* **§6.4:** stratified sampling + operating characteristic (D-31).
* **§7.1:** new keys — `cover\_lat\_sw`, `max\_tier\_span\_sw`, `anchor\_offset\_\*\_s`, `anchor\_tol\_\*\_s`, `finish\_evidence\_min\_k`; all EG-marked; `plausible\_km\_rate\_min\_s` 55 → 65.
* **§8 EC registry:** EC-14 faux départ (DR-03); EC-12 references offset+tol keys.
* **§9:** rename in payload; `piste`, `autostart\_row`, `positions\_lost\_basis\_n`, `realization` tag on `qc`; fixed-decimal canonical floats.
* **§10:** Q-7 = 8 min; `over\_budget` non-waivable unchanged.
* **§11:** §11.4 phase-vocab table (DR-08); `lead\_uncovered\_outside` mapping note (S-1).
* **§12 register:** + detached groups (v1.5), move-detection "first over" events (v1.5), > 14 fields (v2).
* **Annex A:** D-26/D-27 rationale (mask vs label); DR-11 selection-bias paragraph; D-30 note tightening the D-25 defence.

\---

## 7\. Consistency checks performed (reconciliation proof)

1. F-1 × §11.2: text mappings reference states, not the cover *mechanism* — unchanged.
2. F-2 × DoD-1: floors re-referenced to the two masks; no orphaned floor.
3. F-1 × PARKED label: label still uses tier (categorical) while masks use geometry — asymmetry intentional and documented.
4. D-30 × D-25 ladder: rung (i) unchanged; rung (ii) strictly tightened; relegation fixture unaffected; new zero-evidence fixture added.
5. D-29 × S-7: cap 8 and kill-gate "median seeding > 8" are coherent — if the median reaches cap territory, the project stops rather than truncating half its corpus.
6. D-28 × D-22: structural DETACHED in handicap starts is still recorded (D-22) and can no longer distort headline metrics — the two decisions reinforce.
7. D-32 × §7.1/EC-12: quantization confined to canonical export; comparisons and thresholds operate on full precision.
8. D-35 strata × DR-06: `piste` exists before stratified yield reporting needs it.
9. S-1 rename × D-20: one positional sense, documented; the event sense is registered, not mixed in.
10. DR-12 × D-29: marathon races fit the 8-min cap at ≥ 2× playback; the distance-correlated hole closes.
11. EG markers × D-36: every provisional number is enumerated in §4; promotion is mechanically blocked while any marker remains.

Residual conflicts found: none. Precedence if any emerges during drafting: prime directive > decision log > module text > annex.

\---

## 8\. Kill-gates (§0.4 content, values EG)

After OD-1x + a 5-race pilot:

* Median seeding time > 8 min → stop; reconsider CV against pure hand-charting / text-parse.
* M4 tier agreement < 0.85 on pilot hand-labelled frames → recalibrate once; still failing → stop.
* Pilot `chartable` yield < 40% → gate review before any further charting.
* Anchor residual spread (post-offset) > 2 × provisional tolerance on either start type → EC-12 design review before freeze.

\---

## 9\. Execution order

1. Cut **SPEC-2.0.0-draft** from 1.2.0 per §6 (one commit; EG markers in place).
2. Run **OD-1x** (§5) — one afternoon, three replays.
3. Instantiate the EG registry; run the 5-race pilot; evaluate kill-gates (§8).
4. Promote to **2.0.0 FROZEN** in one commit (append D-26…D-36, strip EG markers, changelog).
5. Golden charting (OD-3) begins only against 2.0.0.

*End of RECON-2.0.0.*

