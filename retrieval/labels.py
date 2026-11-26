"""Label matching: emotion compatibility E, relation weight rho, visual compatibility V, anchors and tiers
(RETRIEVAL_METHOD.md sections 2-4). All label ids and weights come from the shared taxonomy."""

SELECTION_WEIGHTS = {"focus": 2.0, "primary": 1.0, "secondary": 0.5}
CONCEPT_WEIGHT = 0.5
EMOTION_SCORES = {"primary": 1.0, "secondary": 0.6}

LITERAL = "relation.literal"
SCENE_ASSOCIATION = "relation.scene_association"
SYMBOLIC = "relation.symbolic"
TIER1_RELATIONS = (LITERAL, SCENE_ASSOCIATION)
# Strength order used to pick the relation an explanation describes.
RELATION_ORDER = {LITERAL: 0, SCENE_ASSOCIATION: 1, SYMBOLIC: 2}


def emotion_match(record, lit_emotion):
    """Return (E, role) for the selected literary emotion, or (None, None) when the record is not eligible.

    E = 1.0 for a primary emotion, 0.6 for a secondary one. neutral / ambiguous / not_annotated records are not
    eligible: that is missing evidence, not a conflict."""
    if record.get("emotion_status") != "has_emotion":
        return None, None
    emotions = record.get("emotions") or {}
    for role in ("primary", "secondary"):
        if any(e.get("id") == lit_emotion for e in emotions.get(role) or []):
            return EMOTION_SCORES[role], role
    return None, None


def emotion_entry(record, lit_emotion, role):
    for e in (record.get("emotions") or {}).get(role) or []:
        if e.get("id") == lit_emotion:
            return e
    return None


def secondary_match(record, secondary_lit_emotion):
    """Ranking preference only: does the record carry the user's second emotion (primary or secondary)?"""
    if not secondary_lit_emotion or record.get("emotion_status") != "has_emotion":
        return False
    emotions = record.get("emotions") or {}
    return any(e.get("id") == secondary_lit_emotion
               for role in ("primary", "secondary") for e in emotions.get(role) or [])


def relation_map(record):
    """{visual target id: visual association} (targets are unique within a record)."""
    return {a["target"]: a for a in record.get("visual_associations") or [] if isinstance(a, dict) and "target" in a}


def rho(relation, symbolic_allowed, relation_weights):
    """Relation weight from taxonomy.relation_weights; symbolic counts only when the user allowed it."""
    if relation is None:
        return 0.0
    if relation == SYMBOLIC and not symbolic_allowed:
        return 0.0
    return float(relation_weights.get(relation, 0.0))


def item_weight(item):
    return SELECTION_WEIGHTS[item["user_selection"]]


def visual_score(rel_map, items, symbolic_allowed, relation_weights):
    """V = sum_x w_x * rho(v, x) / sum_x w_x over the confirmed items; None when there are no items."""
    if not items:
        return None
    total = sum(item_weight(x) for x in items)
    gained = sum(item_weight(x) * rho((rel_map.get(x["id"]) or {}).get("relation"), symbolic_allowed, relation_weights)
                 for x in items)
    return gained / total


def anchors(profile):
    """{focus} when a focus is set, otherwise every confirmed item (in profile order)."""
    items = profile.get("confirmed_visual_items") or []
    focus = [x["id"] for x in items if x.get("user_selection") == "focus"]
    return focus if focus else [x["id"] for x in items]


def qualifying_relations(symbolic_allowed):
    return TIER1_RELATIONS + ((SYMBOLIC,) if symbolic_allowed else ())


def covers_anchor(rel_map, anchor_ids, symbolic_allowed):
    """A qualifying relation (literal / scene_association, or symbolic when allowed) with any anchor."""
    ok = qualifying_relations(symbolic_allowed)
    return any((rel_map.get(a) or {}).get("relation") in ok for a in anchor_ids)


def natural_tier(rel_map, anchor_ids, symbolic_allowed):
    """Eligibility tier of an E-eligible record ignoring tiers_enabled: 1, 2, or 3 (emotion only)."""
    if any((rel_map.get(a) or {}).get("relation") in TIER1_RELATIONS for a in anchor_ids):
        return 1
    if symbolic_allowed and any((rel_map.get(a) or {}).get("relation") == SYMBOLIC for a in anchor_ids):
        return 2
    return 3


def scene_conflict(rel_map, item_ids):
    """Does the record literally depict a scene group the user did not confirm?

    Used only as a tie-break inside tier 3 (engine 1.1.0): an emotion-only fill that names a different scene
    (a mountain verse for a sea photo) contradicts the image, a scene-neutral verse with the same score does not."""
    confirmed = set(item_ids)
    return any(target.startswith("scene_group.") and target not in confirmed and assoc.get("relation") == LITERAL
               for target, assoc in rel_map.items())


def allowed_tier(tier, profile, tiers_enabled):
    """Is a record of this natural tier allowed by the query and the profile?"""
    if tier not in tiers_enabled:
        return False
    if tier == 3:
        return bool(profile.get("emotion_only_allowed"))
    return True


def matched_visuals(rel_map, items, symbolic_allowed, relation_weights):
    """Confirmed items with rho > 0, as parallel (targets, relations) lists in profile order."""
    targets, relations = [], []
    for x in items:
        assoc = rel_map.get(x["id"])
        if assoc and rho(assoc.get("relation"), symbolic_allowed, relation_weights) > 0:
            targets.append(x["id"])
            relations.append(assoc["relation"])
    return targets, relations


def query_terms(profile, taxonomy):
    """[(Arabic term, weight)] for the TF-IDF query: the query_terms_ar of each confirmed item (focus 2,
    primary 1, secondary 0.5) and of the concept (0.5). No emotion terms: emotion is handled by E."""
    out = []
    for x in profile.get("confirmed_visual_items") or []:
        label = taxonomy.labels.get(x["id"]) or {}
        for term in label.get("query_terms_ar") or []:
            out.append((term, item_weight(x)))
    concept = profile.get("concept_id")
    if concept:
        for term in (taxonomy.labels.get(concept) or {}).get("query_terms_ar") or []:
            out.append((term, CONCEPT_WEIGHT))
    return out
