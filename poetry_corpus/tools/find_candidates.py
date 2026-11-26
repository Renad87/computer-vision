"""Find APCD candidate verses for scene-emotion cells (discovery aid for corpus batches; Python stdlib only).

    python3 -m poetry_corpus.tools.find_candidates --cell scene_group.sea:lit_emotion.longing [--cell ...]
        [--all-pilot] [--limit 40] [--per-poet 2] [--grep WORD ...] [--out candidates.tsv]

A candidate is an APCD row whose text matches a scene-group term (taxonomy query terms plus the extensions
below) and, for ranking, literary-emotion cue words. Matching folds diacritics, hamza/alef forms, alef
maqsura and ta marbuta, and allows common proclitics and enclitics. The output is a reading list for the
annotator, nothing more: a lexical hit is never a label, and every chosen verse is read and annotated by
hand (or by the drafting model) before it enters a batch spec.

Skipped: rows already used by any record file, rows with an empty hemistich or Latin letters/digits,
poets whose attribution is widely disputed (EXCLUDED_POETS), and modern-era poets unless MODERN_POETS marks
them public_domain_all (public domain under life + 50, life + 70 and United States rules; see
poetry_corpus/guidelines/copyright_status.md). --allow-modern-risk also admits us_risk and unverified poets.
"""
import argparse
import collections
import re
import sys

from contracts import apcd
from contracts.taxonomy import load_taxonomy

from .coverage import load_records, record_files

DIACRITICS = {chr(c) for c in range(0x064B, 0x0653)} | {"ٰ", "ـ"}
FOLD = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}
PREFIXES = ("", "و", "ف", "ب", "ك", "ل", "ال", "وال", "فال", "بال", "كال", "لل", "ولل", "فلل", "وب", "فب",
            "ول", "فل", "وك", "فك", "يا")
SUFFIXES = ("", "ه", "ها", "هم", "هما", "هن", "ك", "كم", "كما", "ي", "ني", "نا", "ات", "ان", "ين", "ون", "ا")
LATIN_OR_DIGIT = re.compile(r"[A-Za-z0-9]")

# Extensions to the taxonomy query terms (written unvocalized; folded before matching).
EXTRA_SCENE_TERMS = {
    "scene_group.desert": "صحاري البيد الفلا فلوات قفار مفاوز بوادي ركاب ركائب رواحل راحلة مطي مطايا حادي حداة حداء "
                          "خيمة طلول مهمه مهامه سبسب سباسب تنوفة فيافي فيفاء هاجرة هواجر رمضاء قيظ هودج هوادج "
                          "أظعان بعير قلاص نجائب",
    "scene_group.sea": "سواحل شطوط لجج عباب مرسى مرفأ جزيرة ملاحون نوتي زورق قارب خضم حيتان حوت غواص",
    "scene_group.greenery": "حدائق بساتين جنات زهور غصون دوحة أيكة خضراء حقول مروج نخلة خمائل خميلة أقاحي أقحوان "
                            "بنفسج ياسمين شقائق نوار ريحان رياحين زنبق سوسن نسرين خزامى عرار أزاهير ثمار نبات",
    "scene_group.heritage": "خرائب حصون قلاع سور أعمدة قباب كسرى مدائن غمدان الحمراء الزهراء الخورنق السدير "
                            "تدمر بعلبك أهرام الهرمان الهرمين طلول معالم ربع ربوع إرم بنيان",
    "scene_group.sky_night": "ليالي صبح صباح شمس غروب شروق ضحى أصيل عشية مجرة جوزاء سهيل شهب شهاب فرقد فرقدان "
                             "سماك عيوق غسق نهار برق",
}
EMOTION_CUES = {
    "lit_emotion.sadness": "حزن أحزان حزين أسى بكى بكاء بكيت أبكي يبكي تبكي بكت دمع دموع أدمع مدامع عبرة عبرات "
                           "رثاء ثكل ثكلى فقيد فقد فقدت هموم غم كرب كمد شجى شجن أشجان لوعة وجع ألم نوح ناح نعي "
                           "ردى منية منايا موت قبر قبور ضريح جزع حسرة حسرات أسف لهفي رزء رزية مصاب مصيبة نكبة خطوب",
    "lit_emotion.longing": "شوق أشواق مشتاق أشتاق اشتياق حنين حن تحن أحن يحن حنت صبابة وجد ذكرى ذكرت أذكر تذكرت "
                           "ادكار الأحبة الأحباب الوطن أوطان وطني نوى البعد فراق وداع ودعت لقاء اللقاء عودة رجوع "
                           "تشوق تذكار عهد عهود ليت سقى",
    "lit_emotion.awe": "عظيم عظيمة عظمة جلال جليل مهيب هيبة روعة رائع عجب عجيب عجائب أعجب معجز إعجاز سبحان تبارك "
                       "شامخ شاهق ضخم هائل دهش دهشة ذهول حيرة حيران باهر بهر خلود خالد خشوع خاشع بديع إبداع "
                       "رهيب أكبر صنع جبار",
    "lit_emotion.serenity": "هدوء هادئ سكون ساكن سكينة طمأنينة اطمأن أمن أمان راحة نسيم ظل ظلال وادع وديع صفا صفاء "
                            "صافي رقراق ناعم نعيم رضا راض قرير سلام هانئ هناء دعة سجى ساج هدأت ركد صمت تأمل لطيف "
                            "عليل ندى أنس",
    "lit_emotion.joy": "فرح أفراح فرحة سرور مسرور بهجة مبتهج ابتهاج بهيج طرب طربت مطرب ضحك يضحك ضاحك ضاحكا تبسم "
                       "ابتسم بسام باسم مرح نشوة نشوان عيد أعياد عرس هنيئا بشرى بشارة زهو زاهي رقص غناء لهو سعد "
                       "سعادة سعيد حبور جذل جذلان مسرة مسرات تهلل يختال",
    "lit_emotion.loneliness": "غربة غريب وحدة وحيد وحدي منفرد انفراد وحشة مستوحش أنيس غرباء منفى",
    "lit_emotion.pride": "فخر نفخر مجد أمجاد عز عزة شرف كرام أبطال بطل شجاع إقدام حماسة نصر ظفر سيوف رماح",
    "lit_emotion.fear": "خوف خائف رعب رهبة فزع هول أهوال ذعر وجل خشية وحشة مخاوف",
}
EXCLUDED_POETS = ("مجنون ليلى", "قيس بن الملوح", "علي بن أبي طالب", "الشافعي", "الشنفرى", "يزيد بن معاوية",
                  "رابعة العدوية", "فاطمة الزهراء", "عمار بن ياسر", "ورقة بن نوفل")
MODERN_ERA = "الحديث"
# modern-era poets: (death year, status). public_domain_all = public domain under life + 50, life + 70 and
# United States rules (died before 1946, or first published before 1931); see guidelines/copyright_status.md
MODERN_POETS = {
    "محمود سامي البارودي": (1904, "public_domain_all"), "عائشة التيمورية": (1902, "public_domain_all"),
    "حفني ناصف": (1919, "public_domain_all"), "ولي الدين يكن": (1921, "public_domain_all"),
    "سليمان البستاني": (1925, "public_domain_all"), "فوزي المعلوف": (1930, "public_domain_all"),
    "محمد عبد المطلب": (1931, "public_domain_all"), "جبران خليل جبران": (1931, "public_domain_all"),
    "أحمد شوقي": (1932, "public_domain_all"), "حافظ ابراهيم": (1932, "public_domain_all"),
    "أبو القاسم الشابي": (1934, "public_domain_all"), "عبد المحسن الكاظمي": (1935, "public_domain_all"),
    "جميل صدقي الزهاوي": (1936, "public_domain_all"),
    "رشيد أيوب": (1941, "unverified"), "جواد الشبيبي": (1944, "unverified"), "معروف الرصافي": (1945, "unverified"),
    "أحمد محرم": (1945, "unverified"), "نسيب عريضة": (1946, "us_risk"), "أحمد الكاشف": (1948, "us_risk"),
    "خليل مطران": (1949, "us_risk"), "علي محمود طه": (1949, "us_risk"),
    "إبراهيم عبد القادر المازني": (1949, "us_risk"), "إبراهيم ناجي": (1953, "us_risk"),
}


def fold(text):
    return "".join(FOLD.get(ch, ch) for ch in text if ch not in DIACRITICS)


def tokens(text):
    return re.findall(r"[ء-ي]+", fold(text))


def variants(terms):
    """{surface form: term} for every term with the allowed proclitics and enclitics."""
    out = {}
    for term in terms:
        base = fold(term)
        stems = [base] + ([base[:-1] + "ت"] if base.endswith("ه") else [])
        short = len(base) <= 2  # e.g. يم: only the bare word and the article, or «فيما» would match
        for prefix in PREFIXES:
            if (base.startswith("ال") and prefix.endswith("ال")) or (short and prefix and not prefix.endswith("ال")):
                continue
            for stem in stems:
                for suffix in SUFFIXES:
                    if (stem is not base and not suffix) or (short and suffix):
                        continue
                    out.setdefault(prefix + stem + suffix, base)
    return out


def scene_terms(taxonomy, group):
    terms = list(taxonomy.labels[group].get("query_terms_ar") or [])
    for tag in taxonomy.group_members(group)[1]:
        terms += taxonomy.labels[tag].get("query_terms_ar") or []
    return terms + EXTRA_SCENE_TERMS.get(group, "").split()


def used_rows():
    return {r["apcd_row"] for _, r in load_records(record_files())}


def eligible(row, allow_modern_risk=False):
    poet, era = row[apcd.POET], row[apcd.ERA]
    if not row[apcd.SHATR_RIGHT].strip() or not row[apcd.SHATR_LEFT].strip():
        return False
    if LATIN_OR_DIGIT.search(row[apcd.VERSE]) or any(name in poet for name in EXCLUDED_POETS):
        return False
    if era != MODERN_ERA:
        return True
    status = MODERN_POETS.get(poet, (None, None))[1]
    return status == "public_domain_all" or (allow_modern_risk and status is not None)


def search(cells, taxonomy, limit=40, per_poet=2, grep=(), zip_path=None, allow_modern_risk=False):
    """Return {cell: [candidate dict]} ranked by emotion cues, then scene terms, then row number."""
    skip = used_rows()
    lexicons = {}
    for group, emotion in cells:
        lexicons[(group, emotion)] = (variants(scene_terms(taxonomy, group)),
                                      variants(EMOTION_CUES.get(emotion, "").split()))
    must = [fold(word) for word in grep]
    found = collections.defaultdict(list)
    for number, row in apcd.iter_rows(zip_path):
        if number in skip or not eligible(row, allow_modern_risk):
            continue
        words = tokens(row[apcd.VERSE])
        if len(words) < 6:
            continue
        plain = " ".join(words)
        if must and not all(m in plain for m in must):
            continue
        for cell, (scene_map, cue_map) in lexicons.items():
            scene_hits = sorted({scene_map[w] for w in words if w in scene_map})
            if not scene_hits:
                continue
            cue_hits = sorted({cue_map[w] for w in words if w in cue_map})
            found[cell].append({"row": number, "poet": row[apcd.POET], "era": row[apcd.ERA],
                                "meter": row[apcd.METER], "rhyme": row[apcd.RHYME], "text": row[apcd.VERSE],
                                "scene_hits": scene_hits, "cue_hits": cue_hits,
                                "score": 3 * min(len(cue_hits), 3) + 2 * min(len(scene_hits), 2)})
    ranked = {}
    for cell in cells:
        per = collections.Counter()
        out = []
        for cand in sorted(found[cell], key=lambda c: (-c["score"], c["row"])):
            if per[cand["poet"]] >= per_poet:
                continue
            per[cand["poet"]] += 1
            out.append(cand)
            if len(out) >= limit:
                break
        ranked[cell] = out
    return ranked


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cell", action="append", default=[], help="scene_group.X:lit_emotion.Y (repeatable)")
    parser.add_argument("--all-pilot", action="store_true", help="every cell of the taxonomy pilot matrix")
    parser.add_argument("--limit", type=int, default=40, help="candidates per cell")
    parser.add_argument("--per-poet", type=int, default=2, help="candidates per poet per cell")
    parser.add_argument("--grep", nargs="*", default=[], help="folded words that must all occur in the verse")
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    parser.add_argument("--allow-modern-risk", action="store_true",
                        help="also admit modern poets whose US status is a risk or unverified")
    parser.add_argument("--out", default=None, help="TSV path (default: stdout)")
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    cells = [tuple(c.split(":", 1)) for c in args.cell]
    if args.all_pilot:
        cells += [(g, e) for g in taxonomy.pilot["scene_groups"] for e in taxonomy.pilot["lit_emotions"]]
    if not cells:
        parser.error("give --cell or --all-pilot")
    for group, emotion in cells:
        if taxonomy.layer(group) != "scene_group" or taxonomy.layer(emotion) != "lit_emotion":
            parser.error(f"not a scene_group:lit_emotion cell: {group}:{emotion}")
    ranked = search(cells, taxonomy, args.limit, args.per_poet, args.grep, args.apcd_zip, args.allow_modern_risk)
    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        out.write("cell\trow\tpoet\tera\tmeter\trhyme\tscore\tscene_hits\tcue_hits\ttext\n")
        for (group, emotion), cands in ranked.items():
            for c in cands:
                out.write("\t".join([f"{group}:{emotion}", str(c["row"]), c["poet"], c["era"], c["meter"],
                                     c["rhyme"], str(c["score"]), " ".join(c["scene_hits"]),
                                     " ".join(c["cue_hits"]), c["text"]]) + "\n")
    finally:
        if args.out:
            out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
