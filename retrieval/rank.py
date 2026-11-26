"""Score, ordering, diversity / duplicate removal and abstention reasons (RETRIEVAL_METHOD.md sections 5-7)."""

COMPONENTS = ("emotion", "visual", "text", "semantic")
SCORE_DECIMALS = 12  # sort on rounded scores so that float noise can never reorder equal scores


def final_score(scores, weights):
    """final = sum w_i * s_i / sum w_i over the non-null components (null components dropped, weights
    renormalized). No query-level min-max normalization. Returns 0.0 if every weighted component is null."""
    num = den = 0.0
    for name in COMPONENTS:
        s = scores.get(name)
        if s is None:
            continue
        w = float(weights.get(name, 0.0))
        num += w * s
        den += w
    return num / den if den > 0 else 0.0


def sort_key(c):
    """Tier ascending, final descending, secondary-emotion match first, then (engine 1.1.0, ties only) a tier-3
    candidate that does not depict an unconfirmed scene group first, verse_id ascending.

    The scene-conflict key only reorders candidates whose tier, rounded final score and secondary match are equal,
    so the order is still "tier, then final descending" as the recommendations contract requires."""
    return (c["tier"], -round(c["scores"]["final"], SCORE_DECIMALS), 0 if c["secondary_match"] else 1,
            1 if c.get("scene_conflict") else 0, c["record"]["verse_id"])


def poem_key(record):
    """poem_id when set, otherwise (poet, meter, rhyme) as an approximation of the poem."""
    if record.get("poem_id"):
        return ("poem", record["poem_id"])
    source = record.get("source") or {}
    return ("approx", (record.get("poet") or {}).get("name_apcd"), source.get("meter_apcd"), source.get("rhyme_apcd"))


def poet_key(record):
    return (record.get("poet") or {}).get("name_apcd")


def select(candidates, k, diversity, near_dup, max_tier3=1, min_score=0.0):
    """Greedy selection over candidates already sorted by `sort_key`.

    Rules: unique verse_id and text_sha256; at most `max_per_poem` verses per poem; at most `max_per_poet`
    per poet (relaxed, and only this rule, when fewer than k results would remain); no verse whose cosine to a
    selected verse exceeds `near_dup_cosine`; at most `max_tier3` tier-3 items; final >= min_score.
    `near_dup(a, b)` returns the TF-IDF cosine of two records. Returns the selected candidates in rank order.
    """
    max_poem = diversity.get("max_per_poem", 1)
    max_poet = diversity.get("max_per_poet", 1)
    threshold = diversity.get("near_dup_cosine", 0.8)
    pool = [c for c in candidates if c["scores"]["final"] >= min_score]

    chosen, ids, hashes, poems, poets, tier3 = [], set(), set(), {}, {}, [0]

    def admit(c, enforce_poet):
        r = c["record"]
        if r["verse_id"] in ids or r.get("text_sha256") in hashes:
            return False
        if c["tier"] == 3 and max_tier3 is not None and tier3[0] >= max_tier3:
            return False
        if poems.get(poem_key(r), 0) >= max_poem:
            return False
        if enforce_poet and poets.get(poet_key(r), 0) >= max_poet:
            return False
        return not any(near_dup(r, s["record"]) > threshold for s in chosen)

    def take(c):
        r = c["record"]
        chosen.append(c)
        ids.add(r["verse_id"])
        hashes.add(r.get("text_sha256"))
        poems[poem_key(r)] = poems.get(poem_key(r), 0) + 1
        poets[poet_key(r)] = poets.get(poet_key(r), 0) + 1
        tier3[0] += c["tier"] == 3

    # Pass 1 enforces every rule. Pass 2 runs only when fewer than k remain, and relaxes the poet rule only.
    for enforce_poet in (True, False):
        for c in pool:
            if len(chosen) >= k:
                break
            if admit(c, enforce_poet):
                take(c)
        if len(chosen) >= k:
            break
    return sorted(chosen, key=sort_key)


def status_for(n_items, k):
    if n_items == 0:
        return "abstained"
    return "ok" if n_items == k else "partial"


def abstention_reason(stats):
    """First matching reason of RETRIEVAL_METHOD.md section 7, given counts computed by the engine:
    displayable, emotion_eligible, anchor_covered (any emotion), candidates (before section 6)."""
    if stats["displayable"] == 0:
        return "empty_corpus"
    if stats["emotion_eligible"] == 0:
        return "no_emotion_match"
    if stats["candidates"] == 0:
        if stats["anchor_covered"] == 0:
            return "cell_not_covered"
        return "no_visual_match_emotion_only_off"
    return "diversity_exhausted"
