"""Closed enums from SPEC-2.0.0-draft §2, §9, §10. Extending any of these is a version bump."""

BASE_STATES = ("LEADER", "POCKET", "RAIL_COVERED", "RAIL_UNCOVERED", "OUTSIDE_COVERED", "PARKED", "WIDE", "NOT_VISIBLE", "UNKNOWN")
OVERLAYS = ("BREAKING", "DETACHED", "LOW_CONF")
EVENTS = ("BREAK", "SHOT_GAP")  # STRETCH_BLOCK reserved v1.5
SHOT_TYPES = ("wide_pan", "head_on", "tight", "replay_insert", "graphic_fullscreen", "other")
START_TYPES = ("volte", "autostart")
START_FORMATS = ("autostart", "volte_flat", "volte_handicap")
PISTES = ("GP", "PP")
AUTOSTART_ROWS = (1, 2)
VISIBILITY = ("visible", "not_visible", "unknown")
METHOD_FILLER = ("cv_extract", "human_chart", "text_parse")
ID_METHOD = ("human_seed", "propagation", "human_correction")
REVIEW_STATUS = ("pending", "accepted", "rejected")
FIRST_PAST_METHOD = ("official_unrevised", "official_assumed", "observed_crossing", "human_confirm")
TIME_METHOD = ("direct_elapsed", "km_rate_derived", "unavailable")
CHECK_STATUS = ("pass", "mismatch", "inconclusive")
FINISH_CHECK_BASIS = ("provisional", "final_unrevised", "final_assumed", "final_revision_carveout", "unavailable")
ARRIVAL_REVISION_TYPE = ("none", "retrograde", "post_finish_dq", "other", "unknown")
PRODUCER_KIND = ("cv_extract", "human_chart", "text_parse", "config", "pilot_throwaway")  # L-40
SPLIT = ("dev", "heldout")
DAI_UNCAUGHT = ("dai_uncaught_break_expected", "dai_gait_other")  # L-26
