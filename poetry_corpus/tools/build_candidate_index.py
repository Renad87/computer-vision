"""Shared candidate index for parallel corpus workers: one APCD pass, disjoint pools per scene group.

    python3 -m poetry_corpus.tools.build_candidate_index --out DIR [--per-group 1800] [--v3 DIR]

Each eligible APCD row with a scene term goes to exactly one scene group (the most distinct strong scene
terms, ties broken by GROUP_ORDER), so worker pools never overlap. Rows are skipped when they are used by any
record file, fail find_candidates.eligible (empty hemistich, disputed poet, modern poet not public domain
everywhere), have fewer than six words, repeat another candidate or corpus verse after folding diacritics,
or when the same folded verse is attributed to more than one poet anywhere in APCD.

Ranking signals (discovery only, never labels): emotion cue words (find_candidates.EMOTION_CUES) and, when
pyarrow and the V3 parquet hints are available, the old V3 emotion and visual hints. Each pool line carries
the verse, its metadata and up to two neighbouring rows of the same poet on each side for context, and a
half (A: sadness, longing, loneliness, fear; B: awe, serenity, joy, pride) so two workers can share a group
without overlap.
"""
import argparse
import collections
import glob
import json
import os
import sys

from contracts import apcd

from .coverage import load_records, record_files
from .find_candidates import EMOTION_CUES, eligible, fold, tokens, variants

GROUP_ORDER = ["scene_group.worship", "scene_group.city", "scene_group.water", "scene_group.mountains",
               "scene_group.heritage", "scene_group.sea", "scene_group.desert", "scene_group.greenery",
               "scene_group.sky_night"]
STRONG_TERMS = {
    "scene_group.desert": "صحراء صحاري بيداء البيد فلاة الفلا فلوات قفر قفار مفازة مفاوز بادية بوادي رمل رمال كثيب "
                          "كثبان سراب هجير ظعائن ظعن نوق ناقة عيس ركائب ركاب رواحل مطايا حادي حداة خيام خيمة طلل "
                          "أطلال طلول دمن دمنة مهمه مهامه سبسب سباسب تنوفة فيافي هودج هوادج أظعان بعير قلاص الغضا",
    "scene_group.sea": "بحر البحر بحار موج أمواج ساحل سواحل شاطئ شط لجة لجج اليم زبد سفينة سفن شراع مركب ملاح "
                       "مرسى مرفأ جزيرة عباب خضم حيتان غواص",
    "scene_group.mountains": "جبل جبال قمة قمم ذرى ذروة شاهق شواهق هضبة هضاب وعر صخر صخور واد وادي أودية وديان طود "
                             "أطواد سفح ثلج ثلوج جليد كهف",
    "scene_group.water": "نهر أنهار جدول جداول غدير غدران نبع ينبوع ينابيع بحيرة شلال ساقية سواقي الفرات دجلة النيل "
                         "بردى نواعير ناعورة ضفاف",
    "scene_group.greenery": "روض روضة رياض حديقة حدائق بستان بساتين زهر أزهار زهور نرجس شجر أشجار غصن أغصان غصون "
                            "دوح دوحة أيك أيكة خضراء ربيع زرع حقل حقول سنابل مرج مروج عشب نخل نخيل نخلة خمائل خميلة "
                            "أقاحي أقحوان بنفسج ياسمين شقائق نوار ريحان رياحين زنبق سوسن نسرين خزامى عرار أزاهير",
    "scene_group.heritage": "قصر قصور إيوان آثار خرائب حصن حصون قلعة قلاع أسوار مدائن كسرى غمدان الحمراء الزهراء "
                            "الخورنق السدير تدمر بعلبك أهرام الهرمان الهرمين صرح إرم سوق أسواق",
    "scene_group.sky_night": "سماء السماء أفق ليل الليل ليلة ليالي نجم نجوم كوكب كواكب قمر بدر هلال ثريا فجر شفق "
                             "سحاب غيم دجى ظلام صبح صباح شمس غروب شروق أصيل عشية مجرة جوزاء سهيل شهب شهاب فرقد غسق",
    "scene_group.city": "مدينة مدن حاضرة عمران شارع شوارع ميدان بغداد دمشق جلق القاهرة قرطبة إشبيلية بلنسية القيروان "
                        "حلب البصرة الكوفة الموصل الإسكندرية الزوراء",
    "scene_group.worship": "مسجد مساجد جامع محراب منبر مئذنة مآذن أذان المؤذن صلاة الكعبة الحرم المصلى دير أديرة "
                           "كنيسة كنائس صومعة راهب رهبان ناقوس نواقيس بيعة زمزم عرفات المشعر",
}
HALF_A = {"lit_emotion.sadness", "lit_emotion.longing", "lit_emotion.loneliness", "lit_emotion.fear"}
V3_EMOTIONS = {
    "emotion.sadness": "lit_emotion.sadness", "emotion.grief": "lit_emotion.sadness",
    "emotion.despair": "lit_emotion.sadness", "emotion.regret": "lit_emotion.sadness",
    "emotion.longing": "lit_emotion.longing", "emotion.nostalgia": "lit_emotion.longing",
    "emotion.awe": "lit_emotion.awe", "emotion.admiration": "lit_emotion.awe",
    "emotion.calmness": "lit_emotion.serenity", "emotion.joy": "lit_emotion.joy",
    "emotion.loneliness": "lit_emotion.loneliness", "emotion.pride": "lit_emotion.pride",
    "emotion.fear": "lit_emotion.fear",
}
V3_VISUAL = {
    "visual_object.sea": "scene_group.sea", "visual_object.ship": "scene_group.sea",
    "visual_object.desert": "scene_group.desert", "visual_object.camel": "scene_group.desert",
    "visual_object.mountain": "scene_group.mountains", "visual_object.river": "scene_group.water",
    "visual_object.garden": "scene_group.greenery", "visual_object.flowers": "scene_group.greenery",
    "visual_object.tree": "scene_group.greenery", "visual_object.palace": "scene_group.heritage",
    "visual_object.ruins": "scene_group.heritage", "visual_object.city": "scene_group.city",
    "visual_object.stars": "scene_group.sky_night", "visual_object.moon": "scene_group.sky_night",
    "visual_object.sky": "scene_group.sky_night", "visual_object.sun": "scene_group.sky_night",
    "visual_scene.night": "scene_group.sky_night", "visual_scene.sunrise": "scene_group.sky_night",
    "visual_scene.sunset": "scene_group.sky_night", "visual_scene.garden_scene": "scene_group.greenery",
    "visual_scene.abandoned_place": "scene_group.desert",
}
DEFAULT_V3 = os.path.join(os.path.dirname(apcd.DEFAULT_ZIP), "work", "apcd-semantic-v3", "parquet")


def folded_key(text):
    return "".join(ch for ch in fold(text) if not ch.isspace())


def load_v3(rows, v3_dir):
    """{row: (lit emotions, scene groups)} from the V3 parquet hints, or {} when unavailable."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {}
    paths = sorted(glob.glob(os.path.join(v3_dir, "*.parquet")))
    wanted, out = set(rows), {}
    cols = ["apcd_row", "v3_emotions_expressed", "v3_emotions_inferred", "v3_visual_objects", "v3_visual_scenes"]
    for path in paths:
        table = pq.read_table(path, columns=cols)
        numbers = table.column("apcd_row").to_pylist()
        if not wanted.intersection(numbers):
            continue
        data = {c: table.column(c).to_pylist() for c in cols[1:]}
        for i, number in enumerate(numbers):
            if number not in wanted:
                continue
            emotions = {V3_EMOTIONS[e] for col in cols[1:3] for e in (data[col][i] or []) if e in V3_EMOTIONS}
            groups = {V3_VISUAL[v] for col in cols[3:] for v in (data[col][i] or []) if v in V3_VISUAL}
            out[number] = (sorted(emotions), sorted(groups))
    return out


def build(out_dir, per_group=1800, per_poet=10, v3_dir=DEFAULT_V3, zip_path=None):
    corpus = [r for _, r in load_records(record_files())]
    used_rows = {r["apcd_row"] for r in corpus}
    used_folded = {folded_key(r["text_original"]) for r in corpus}
    scene_maps = {g: variants(STRONG_TERMS[g].split()) for g in GROUP_ORDER}
    cue_maps = {e: variants(EMOTION_CUES[e].split()) for e in EMOTION_CUES}

    candidates = {}
    for number, row in apcd.iter_rows(zip_path):
        if number in used_rows or not eligible(row):
            continue
        words = tokens(row[apcd.VERSE])
        if len(words) < 6:
            continue
        hits = {g: sorted({m[w] for w in words if w in m}) for g, m in scene_maps.items()}
        hits = {g: h for g, h in hits.items() if h}
        if not hits:
            continue
        group = max(hits, key=lambda g: (len(hits[g]), -GROUP_ORDER.index(g)))
        cues = {e: sorted({m[w] for w in words if w in m}) for e, m in cue_maps.items()}
        cues = {e: c for e, c in cues.items() if c}
        candidates[number] = {"row": number, "group": group, "scene_hits": hits[group],
                              "other_groups": sorted(g for g in hits if g != group), "cues": cues,
                              "folded": folded_key(row[apcd.VERSE]), "poet": row[apcd.POET]}

    # attribution conflicts: the same folded verse under another poet anywhere in APCD
    by_folded = collections.defaultdict(set)
    for c in candidates.values():
        by_folded[c["folded"]].add(c["poet"])
    wanted = set(by_folded)
    for number, row in apcd.iter_rows(zip_path):
        key = folded_key(row[apcd.VERSE])
        if key in wanted:
            by_folded[key].add(row[apcd.POET])
    v3 = load_v3(list(candidates), v3_dir) if v3_dir and os.path.isdir(v3_dir) else {}

    pools = collections.defaultdict(list)
    seen_folded = set(used_folded)
    for number in sorted(candidates):
        c = candidates[number]
        if len(by_folded[c["folded"]]) > 1 or c["folded"] in seen_folded:
            continue
        seen_folded.add(c["folded"])
        v3_emotions, v3_groups = v3.get(number, ([], []))
        c["v3_emotions"], c["v3_groups"] = v3_emotions, v3_groups
        c["score"] = (3 * min(len(c["cues"]), 2) + 2 * min(len(c["scene_hits"]), 2)
                      + 2 * bool(v3_emotions) + (c["group"] in v3_groups))
        pools[c["group"]].append(c)

    selected = {}
    for group, items in pools.items():
        per = collections.Counter()
        keep = []
        for c in sorted(items, key=lambda c: (-c["score"], c["row"])):
            if per[c["poet"]] >= per_poet:
                continue
            per[c["poet"]] += 1
            keep.append(c)
            if len(keep) >= per_group:
                break
        selected[group] = keep

    need = set()
    for keep in selected.values():
        for c in keep:
            need.update(range(max(0, c["row"] - 2), c["row"] + 3))
    rows = apcd.get_rows(need, zip_path)
    os.makedirs(out_dir, exist_ok=True)
    summary = {"pools": {}, "skipped_multi_poet": sum(1 for k, v in by_folded.items() if len(v) > 1)}
    for group, keep in selected.items():
        name = group.split(".", 1)[1]
        halves = collections.Counter()
        with open(os.path.join(out_dir, f"{name}.jsonl"), "w", encoding="utf-8") as fh:
            for i, c in enumerate(keep):
                row = rows[c["row"]]
                emotions = set(c["cues"]) | set(c["v3_emotions"])
                if emotions & HALF_A and not emotions - HALF_A:
                    half = "A"
                elif emotions - HALF_A and not emotions & HALF_A:
                    half = "B"
                else:
                    half = "A" if i % 2 == 0 else "B"
                halves[half] += 1
                context = [[n, rows[n][apcd.VERSE]] for n in range(c["row"] - 2, c["row"] + 3)
                           if n != c["row"] and n in rows and rows[n][apcd.POET] == row[apcd.POET]]
                fh.write(json.dumps({
                    "row": c["row"], "half": half, "poet": row[apcd.POET], "era": row[apcd.ERA],
                    "meter": row[apcd.METER], "rhyme": row[apcd.RHYME], "diwan": row[apcd.DIWAN],
                    "text": row[apcd.VERSE], "group": group, "scene_hits": c["scene_hits"],
                    "other_groups": c["other_groups"], "cue_hits": c["cues"], "v3_hint_emotions": c["v3_emotions"],
                    "v3_hint_groups": c["v3_groups"], "context": context}, ensure_ascii=False) + "\n")
        summary["pools"][group] = {"candidates_in_apcd": len(pools[group]), "in_pool": len(keep),
                                   "half_A": halves["A"], "half_B": halves["B"]}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--per-group", type=int, default=1800)
    parser.add_argument("--per-poet", type=int, default=10)
    parser.add_argument("--v3", default=DEFAULT_V3)
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.out, args.per_group, args.per_poet, args.v3, args.apcd_zip), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
