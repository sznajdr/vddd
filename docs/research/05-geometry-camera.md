# 05 — Pack geometry, camera motion, calibration (M4, D-07, §3.3, RP-5)

## Question
Does the field offer anything better than pack-relative coordinates for a panning, zooming broadcast of a track with no markings? And how do trackers cope with the pan?

## Findings

- **Sports field registration needs templates.** TVCalib (WACV 2023) estimates pinhole parameters from segment correspondences to a known pitch model; PnLCalib (2024) optimises points and lines against a 3D field model with predefined keypoints and reports top results on SoccerNet-Calibration / WorldCup 2014 / TS-WorldCup. Both motivate themselves with partial markings in close-ups; nothing was found that calibrates with **no** markings. ([TVCalib](https://arxiv.org/pdf/2207.11709), [PnLCalib](https://www.arxiv.org/abs/2404.08401))
- **SoccerNet 2025 Game State Reconstruction** converged on tracking-by-detection; the differentiators are identity modelling and calibration. Baseline GS-HOTA 29.0 vs best 63.9. ([SoccerNet 2025 results](https://arxiv.org/pdf/2508.19182))
- **Camera motion compensation in trackers:** BoT-SORT registers consecutive frames (sparse features / ECC) and corrects the Kalman prediction; it is the mechanism meant for pans; it degrades on low-texture backgrounds. ([BoT-SORT](https://arxiv.org/pdf/2206.14651), [Roboflow docs](https://trackers.roboflow.com/latest/trackers/botsort/))
- **Peloton analogues:** cycling drafting detection has been done from a bike-mounted camera with geometric distance estimation and LiDAR ground truth (Sensors 2020), not from broadcast; CyclingTrack (2026) is an aerial MOT benchmark; broadcast rider identification reads race numbers from side views. The pack-relative idea has no published broadcast precedent, which is consistent with D-07 being a deliberate simplification rather than a known technique. ([Allebosch et al. 2020](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7085662/), [Velo/IDLab article](https://velo.outsideonline.com/road/road-racing/could-ai-be-the-future-of-bike-race-coverage/?scope=anon))

## Finding from the synthetic pilot (2026-11-04)

With 0.3 px box jitter and ~4 px displacements per 0.4 s window, the per-frame motion axis tilted by up to 7° on individual frames. Because `Δw ≈ (SL/SW)·l·sin δ`, a 7° tilt displaces a runner 5 SL back by ≈ 1.7 SL-equivalents = ~5 SW: every lane merges and the frame's tiers go `UNKNOWN`. The requirement implied by `same_tier_sw = 0.6` on a 5 SL pack is about **1° axis accuracy**. Fixes applied: length-weighted axial mean, minimum displacement `axis_min_vector_sl`, temporal smoothing `axis_smooth_s` (RP-21). This is independent of RP-5 and compounds it.

## Simulator results (2026-11-04)

See `11-simulated-geometry.md`: lateral compression ≈ height/depth; linear two-line scale fails under perspective; projective lateral coordinate + rail-line axis + polyline datum + foot-point correction restore tiering in the model (RP-19 refined, RP-20 resolved, RP-22, RP-23); elevation per section bounds what any method can do (RP-24).

## Implications for the spec

1. **The homography ban (§3.3) is justified by the literature**, not only by caution: every working calibration method assumes a marked template. Re-entry remains conditional on a calibration source (§12).
2. **What a trot track does offer:** the inner rail and the outer fence are two roughly parallel curves. In a wide pan they give a *vanishing direction* for the track axis, which is a better `u_long` prior than runner motion when the pack is nearly stationary in frame (the §3.1 fallback case). Proposal for M4 projection (`projection.py`): detect the rail line with a lightweight segmenter or Hough on the OD-1x frames; use its direction as the PCA fallback's prior; never use it for metric scale. Non-numeric choice → `extractor_version`.
3. **RP-5 lateral scale stands as the top geometric risk.** Nothing in the literature estimates lateral spacing from an oblique broadcast without a template; the honest fix is measurement (OD-1x step 4) and, if needed, a per-shot `sw_ratio` from the rail-to-fence apparent width at the pack's screen position (both curves are at known real-world separation at Vincennes, which is a single scalar the owner can look up or pace out). That would be a scale calibration from two parallel lines, not a homography, and could be allowed under §3.3 as an SL/SW normalisation aid. Owner decision.
4. **Tracker CMC settings** belong in `m3_track.gmc_method` ∈ {none, sparseOptFlow, ecc, orb}; the pilot compares them on the same races.
5. **Bends:** the straight-axis error on bends (≈ 1 SW on a 40 m pack at 115 m radius, RECON-patch estimate) can be reduced by fitting `u_long` on a *local* neighbourhood (nearest k runners) instead of the whole pack. Config `geometry.axis_neighbourhood_k` (0 = whole pack). Evidence-gated by OD-1x bend frames.
