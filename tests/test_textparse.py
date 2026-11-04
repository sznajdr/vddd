from tripstate.textparse import FAMILIES, candidates_for, normalize, parse_notule


def seg(res, status=None):
    return [s for s in res.segments if status is None or s["mapping_status"] == status]


def test_normalize():
    assert normalize("  Nez au vent, en 2\u00e8me \u00e9paisseur\u2026 L\u2019animateur \u00bb") == 'nez au vent, en 2eme epaisseur\u2026 l\'animateur "'


def test_candidates_from_dimensions():
    assert candidates_for({"covered": True, "depth": 1}) == ["OUTSIDE_COVERED", "POCKET"]
    assert candidates_for({"covered": False}) == ["LEADER", "PARKED", "RAIL_UNCOVERED", "WIDE"]
    assert candidates_for({"tier": 1, "covered": True, "depth": 2}) == ["RAIL_COVERED"]
    assert candidates_for({"tier": 2, "covered": False}) == ["PARKED"]


def test_direct_leader_and_pocket_ambiguity():
    r = parse_notule("En tête dès le départ, a dicté sa loi.", "r1", 4, "t1")
    s = seg(r, "resolved")
    assert s and s[0]["state"] == "LEADER" and s[0]["phase"] == "early" and s[0]["mapping_confidence"] == 1.0
    assert s[0]["covered"] is False and s[0]["method"] == "text_parse" and s[0]["t_start_frac"] is None
    r = parse_notule("Dans le dos de l'animateur à mi-parcours.", "r1", 5)
    a = seg(r, "ambiguous")
    assert a and a[0]["candidate_states"] == ["OUTSIDE_COVERED", "POCKET"] and a[0]["state"] is None and a[0]["phase"] == "mid"


def test_conjunction_resolves_rail_uncovered_and_parked():
    r = parse_notule("Sans dos à la corde dans le dernier tournant.", "r", 1)
    s = seg(r, "resolved")
    assert s and s[0]["state"] == "RAIL_UNCOVERED" and s[0]["mapping_confidence"] == 0.8 and s[0]["phase"] == "late"
    r = parse_notule("Nez au vent en deuxième épaisseur.", "r", 2)
    s = seg(r, "resolved")
    assert s and s[0]["state"] == "PARKED" and s[0]["lead_uncovered_outside"] is False
    r = parse_notule("À hauteur de l'animateur sur la fin.", "r", 3)
    s = seg(r, "resolved")
    assert s and s[0]["state"] == "PARKED" and s[0]["lead_uncovered_outside"] is True


def test_bare_phrases_stay_unresolved():
    r = parse_notule("Nez au vent.", "r", 1)
    a = seg(r, "ambiguous")
    assert a and set(a[0]["candidate_states"]) == {"LEADER", "PARKED", "RAIL_UNCOVERED", "WIDE"}
    r = parse_notule("En dehors.", "r", 1)
    assert seg(r, "ambiguous")[0]["candidate_states"] == ["OUTSIDE_COVERED", "PARKED"]
    r = parse_notule("Dans un dos.", "r", 1)
    assert "POCKET" in seg(r, "ambiguous")[0]["candidate_states"] and "OUTSIDE_COVERED" in seg(r, "ambiguous")[0]["candidate_states"]


def test_wide_and_numbered_rail_lines():
    r = parse_notule("En troisième épaisseur dans la montée.", "r", 9)
    s = seg(r, "resolved")
    assert s[0]["state"] == "WIDE" and s[0]["tier_attr"] == 3 and s[0]["phase"] == "late"
    r = parse_notule("Deuxième ligne à la corde.", "r", 9)
    assert seg(r, "resolved")[0]["state"] == "POCKET"
    r = parse_notule("Troisième ligne à la corde.", "r", 9)
    assert seg(r, "resolved")[0]["state"] == "RAIL_COVERED"


def test_negation_quotes_and_other_subject_are_not_asserted():
    r = parse_notule("N'a jamais trouvé le dos.", "r", 1)
    assert not seg(r) and any(h.negated for h in r.hits)
    r = parse_notule('Le driver a dit "en tête c\'était impossible".', "r", 1)
    assert not seg(r) and any(h.scope == "quoted" for h in r.hits)
    r = parse_notule("Le 7 en tête l'a gêné.", "r", 1)
    assert not seg(r) and any(h.scope == "other" for h in r.hits)


def test_breaks_and_exclusions():
    r = parse_notule("S'est enlevé au départ, remis au trot, a fini vite.", "r", 6)
    assert len(r.events) == 1 and r.events[0]["recovered"] is True and r.events[0]["review_status"] == "pending" and r.events[0]["phase"] == "early"
    r = parse_notule("A fait une faute dans le dernier tournant.", "r", 6)
    assert len(r.events) == 1 and r.events[0]["recovered"] is None and r.events[0]["phase"] == "late"
    r = parse_notule("Disqualifié pour allures irrégulières.", "r", 6)
    assert not r.events and "dai_mention" in {h.family for h in r.hits}
    r = parse_notule("Rétrogradé après enquête. A rapidement faibli.", "r", 6)
    assert not r.events and not seg(r)


def test_detached_overlay_ends():
    r = parse_notule("En tête, s'est détaché dans la ligne droite.", "r", 1)
    ov = [s for s in r.segments if s["state_kind"] == "overlay"]
    assert ov and ov[0]["end_attr"] == "front" and ov[0]["phase"] == "stretch"
    r = parse_notule("Attardé, loin du groupe.", "r", 2)
    ov = [s for s in r.segments if s["state_kind"] == "overlay"]
    assert ov and all(o["end_attr"] == "rear" for o in ov)
    r = parse_notule("En queue de peloton.", "r", 2)
    assert not [s for s in r.segments if s["state_kind"] == "overlay"]


def test_reserved_stretch_block_recorded_not_emitted():
    r = parse_notule("Bloqué, n'a jamais pu s'exprimer dans la ligne droite.", "r", 3)
    assert not seg(r) and any(h.target == "RESERVED:STRETCH_BLOCK" for h in r.hits)


def test_every_family_regex_compiles_and_has_evidence_flag():
    for f in FAMILIES:
        assert f.regex and f.evidence in ("C", "P", "")
