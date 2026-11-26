"""Emotion review sheet for Renad's P0 package: column contract, workbook/CSV writers and a checker.

Review contract (approved in the planning handoff), in this order:
    verse_id, text_original, poet, proposed_primary, proposed_secondary, evidence_text, justification_ar,
    decision, corrected_primary, corrected_secondary, note
followed by read-only context columns (era, apcd_row, source, ...). The CSV uses taxonomy ids
(lit_emotion.*); the workbook shows Arabic names and offers dropdowns. Reviewer fields are always empty
when generated.

    python3 -m poetry_corpus.tools.review_sheet check <returned.xlsx|.csv> [--final]
    python3 -m poetry_corpus.tools.review_sheet export-csv <returned.xlsx> <out.csv>
"""
import argparse
import csv
import json
import os
import re
import sys

from contracts.taxonomy import load_taxonomy
from contracts.validate import load_jsonl

from .xlsx import Workbook, col_letter, read_workbook

CONTRACT_COLUMNS = ["verse_id", "text_original", "poet", "proposed_primary", "proposed_secondary",
                    "evidence_text", "justification_ar", "decision", "corrected_primary", "corrected_secondary",
                    "note"]
CONTEXT_COLUMNS = ["era", "apcd_row", "source", "attribution_status", "proposed_visual_labels", "meaning_ar",
                   "text_note", "annotation_method", "annotation_model_id", "review_status"]
CSV_COLUMNS = CONTRACT_COLUMNS + CONTEXT_COLUMNS
REVIEWER_FIELDS = ("decision", "corrected_primary", "corrected_secondary", "note")
DECISIONS = ("ACCEPT", "CORRECT", "REJECT", "UNSURE")
NONE_AR = "لا يوجد"
NOTE_MAX_WORDS = 20
SHEET_INSTRUCTIONS, SHEET_EMOTIONS, SHEET_REVIEW = "التعليمات", "الأحاسيس الثمانية", "المراجعة"
SEPARATOR_IDS, SEPARATOR_AR = "|", "، "

# workbook column order: (field, Arabic header, width, style)
XLSX_COLUMNS = [
    ("n", "رقم", 6, "number"),
    ("text_original", "البيت كما في APCD", 46, "verse"),
    ("meaning_ar", "المعنى (مسودة)", 38, "text"),
    ("poet", "الشاعر", 16, "text"),
    ("proposed_primary", "الإحساس الأساسي المقترح", 16, "text"),
    ("proposed_secondary", "الإحساسات الثانوية المقترحة", 18, "text"),
    ("evidence_text", "الدليل النصي من البيت", 24, "text"),
    ("justification_ar", "مبرر التصنيف", 34, "text"),
    ("decision", "القرار", 13, "editable"),
    ("corrected_primary", "الأساسي المصحح", 18, "editable"),
    ("corrected_secondary", "الثانوي المصحح", 18, "editable"),
    ("note", "ملاحظة المراجِعة", 32, "editable"),
    ("era", "العصر", 14, "text"),
    ("proposed_visual_labels", "الوسوم البصرية المقترحة", 30, "text"),
    ("verse_id", "معرّف البيت", 17, "text"),
    ("apcd_row", "صف APCD", 10, "number"),
    ("text_note", "ملاحظة على نص APCD", 30, "text"),
    ("source", "المصدر المتاح", 34, "text"),
    ("attribution_status", "حالة النسبة", 16, "text"),
    ("annotation_method", "حالة التعليق", 26, "text"),
]
# optional columns for later packages (P1+); the P0 workbook uses neither
VISUAL_DECISIONS = ("ACCEPT", "REJECT", "UNSURE")
VISUAL_COLUMN = ("visual_decision", "قرار الوسم البصري", 14, "editable")
PRIORITY_COLUMN = ("priority", "الأولوية", 9, "text")
ATTRIBUTION_AR = {"apcd_only": "من APCD وحده", "source_verified": "موثّقة في قاعدة المعرفة", "disputed": "مختلف فيها"}
METHOD_AR = "مسودة آلية (ai_draft) بانتظار مراجعة بشرية"


def header_text(field, header_ar):
    return header_ar if field == "n" else f"{header_ar} ({field})"


RLE, PDF = "‫", "‬"


def rtl(text):
    """Explanatory text only (never data cells): force right-to-left order even in viewers that ignore the
    sheet direction (for example macOS Quick Look), so mixed Arabic/Latin lines read correctly."""
    return f"{RLE}{text}{PDF}"


# --------------------------------------------------------------------------------------------- building rows
def name_ar(taxonomy, label_id):
    return taxonomy.labels[label_id]["name_ar"]


def build_rows(records, taxonomy, kb_titles=None):
    """One row per draft record. Returns [{field: (csv value, display value)}]."""
    rows = []
    for n, record in enumerate(records, 1):
        emotions = record["emotions"]
        primary = emotions["primary"][0]
        secondary = emotions["secondary"]
        justification = primary.get("justification_ar") or ""
        for entry in secondary:
            if entry.get("justification_ar"):
                justification += f"؛ ثانوي ({name_ar(taxonomy, entry['id'])}): {entry['justification_ar']}"
        visual_ids = SEPARATOR_IDS.join(f"{a['target']}:{a['relation']}" for a in record["visual_associations"])
        visual_ar = "؛ ".join(f"{name_ar(taxonomy, a['target'])} — {name_ar(taxonomy, a['relation'])}"
                             for a in record["visual_associations"])
        source = f"APCD، {record['source']['diwan_apcd']}، الصف {record['apcd_row']}"
        if record.get("poem_id"):
            source += f"؛ قاعدة المعرفة التاريخية: {record['poem_id']} ({'، '.join(record['evidence_ids'])})"
        evidence = (primary.get("evidence_span") or {}).get("text", "")
        row = {
            "n": (n, n),
            "verse_id": (record["verse_id"], record["verse_id"]),
            "text_original": (record["text_original"], record["text_original"]),
            "poet": (record["poet"]["name_apcd"], record["poet"]["name_apcd"]),
            "proposed_primary": (primary["id"], name_ar(taxonomy, primary["id"])),
            "proposed_secondary": (SEPARATOR_IDS.join(e["id"] for e in secondary),
                                   SEPARATOR_AR.join(name_ar(taxonomy, e["id"]) for e in secondary) or NONE_AR),
            "evidence_text": (evidence, evidence),
            "justification_ar": (justification, justification),
            "decision": ("", ""), "corrected_primary": ("", ""), "corrected_secondary": ("", ""), "note": ("", ""),
            "era": (record["era_apcd"], record["era_apcd"]),
            "apcd_row": (record["apcd_row"], record["apcd_row"]),
            "source": (source, source),
            "attribution_status": (record["attribution_status"], ATTRIBUTION_AR[record["attribution_status"]]),
            "proposed_visual_labels": (visual_ids, visual_ar or NONE_AR),
            "meaning_ar": (record.get("meaning_ar") or "", record.get("meaning_ar") or ""),
            "text_note": (record.get("text_note") or "", record.get("text_note") or ""),
            "annotation_method": (record["annotation"]["method"], METHOD_AR),
            "annotation_model_id": (record["annotation"]["model_id"], record["annotation"]["model_id"]),
            "review_status": (record["review"]["status"], record["review"]["status"]),
            "visual_decision": ("", ""),
            "priority": ("", ""),
        }
        rows.append(row)
    return rows


def write_csv(rows, path, columns=None):
    """UTF-8 with BOM (opens correctly in Excel); taxonomy ids for emotions; reviewer fields empty."""
    columns = columns or CSV_COLUMNS
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row[field][0] for field in columns])


def workbook_columns(visual=False, priority=False):
    """XLSX_COLUMNS, optionally with the priority column after the row number and the visual decision after
    the note."""
    columns = list(XLSX_COLUMNS)
    if priority:
        columns.insert(1, PRIORITY_COLUMN)
    if visual:
        columns.insert([c[0] for c in columns].index("note") + 1, VISUAL_COLUMN)
    return columns


def _row_height(row, columns=XLSX_COLUMNS):
    lines = 1
    for field, _, width, style in columns:
        text = str(row[field][1])
        per_line = max(1, int(width * (1.0 if style == "verse" else 1.25)))
        lines = max(lines, -(-len(text) // per_line) + text.count("\n"))
    return min(160, 8 + lines * 19)


def write_workbook(rows, taxonomy, path, emotion_ids, title=None, book_title=None,
                   return_name="renad_review_v1.xlsx", visual=False, priority=False):
    """Write the review workbook. The defaults reproduce the P0 package exactly; later packages pass their
    own title and return file name, and may add the priority column and the visual decision column."""
    columns = workbook_columns(visual, priority)
    book = Workbook(title=book_title or "مراجعة إحساس أبيات P0")
    lit_names = [name_ar(taxonomy, e) for e in emotion_ids]
    last = len(rows) + 1
    col = {field: i for i, (field, _, _, _) in enumerate(columns, 1)}
    decision_range = f"{col_letter(col['decision'])}2:{col_letter(col['decision'])}{last}"

    # sheet 1: instructions
    s = book.add_sheet(SHEET_INSTRUCTIONS)
    s.widths = {1: 14, 2: 22, 3: 22, 4: 22, 5: 34}
    s.set(1, 1, rtl(title or "مراجعة إحساس الأبيات — حزمة P0 (40 بيتًا)"), "title")
    s.merges.append("A1:E1")
    s.heights[1] = 30
    steps = [
        "افتحي ورقة «المراجعة». كل صف بيت حقيقي منقول حرفيًا من APCD؛ لا تعدّلي نص البيت.",
        "اقرئي البيت ومعناه، ثم الإحساس الأساسي والثانوي المقترحين والدليل النصي والمبرر.",
        "في عمود «القرار» اختاري من القائمة: ACCEPT (أوافق) أو CORRECT (أصحح) أو REJECT (أرفض) أو UNSURE (غير متأكدة).",
        "عند CORRECT اختاري الإحساس الصحيح من «الأساسي المصحح» و/أو «الثانوي المصحح» (القائمة نفسها، و«لا يوجد» للثانوي).",
        "عند REJECT أو UNSURE اكتبي ملاحظة قصيرة في «ملاحظة المراجِعة» (20 كلمة كحد أقصى).",
        "عند ACCEPT اتركي أعمدة التصحيح فارغة. الملاحظة اختيارية.",
        "المقترحات مسودات آلية (ai_draft) أعدها نموذج لغوي، وليست أحكامًا بشرية؛ حكمك أنتِ هو المرجع.",
        "احكمي على الإحساس الغالب على البيت كله، لا على كلمة معزولة. التفاصيل في annotation_guide_ar.md.",
        f"احفظي الملف وأعيديه إلى عمر باسم {return_name}.",
    ]
    if visual:
        steps.insert(5, "في «قرار الوسم البصري» احكمي على الوسوم البصرية المقترحة (مثل: البحر — حرفية): ACCEPT إن صحت، "
                        "REJECT إن لم تصح، UNSURE عند الشك؛ ومع REJECT أو UNSURE اكتبي ملاحظة.")
    s.set(3, 1, "الخطوة", "header")
    s.set(3, 2, "التعليمات", "header")
    s.merges.append("B3:E3")
    for i, step in enumerate(steps, 1):
        r = 3 + i
        s.set(r, 1, i, "number")
        s.set(r, 2, rtl(step), "text")
        s.merges.append(f"B{r}:E{r}")
        s.heights[r] = 36
    r = 4 + len(steps) + 1
    s.set(r, 1, "المفتاح", "subtitle")
    s.set(r, 2, "", "editable")
    yellow = "القرار، الأساسي المصحح، الثانوي المصحح، ملاحظة المراجِعة" + ("، قرار الوسم البصري" if visual else "")
    s.set(r, 3, rtl(f"الخلايا الصفراء في ورقة «المراجعة» (الأعمدة: {yellow}) هي وحدها ما تعبئينه."), "text")
    s.merges.append(f"C{r}:E{r}")
    s.heights[r] = 36
    r += 2
    review_ref = f"'{SHEET_REVIEW}'!{decision_range}"
    s.set(r, 1, "التقدم", "subtitle")
    s.set(r, 2, "أبيات فيها قرار", "text")
    s.formula(r, 3, f"COUNTA({review_ref})", 0)
    s.set(r + 1, 2, "أبيات متبقية", "text")
    s.formula(r + 1, 3, f"{len(rows)}-COUNTA({review_ref})", len(rows))
    r += 3
    s.set(r, 1, "مثال توضيحي", "subtitle")
    s.set(r, 2, rtl("هذا الصف مثال لطريقة التعبئة فقط، وليس قرارًا على أي بيت من أبيات المراجعة."), "note")
    s.merges.append(f"B{r}:E{r}")
    s.set(r + 1, 1, "القرار", "header")
    s.set(r + 1, 2, "الأساسي المصحح", "header")
    s.set(r + 1, 3, "الثانوي المصحح", "header")
    s.set(r + 1, 4, "ملاحظة المراجِعة", "header")
    s.merges.append(f"D{r + 1}:E{r + 1}")
    s.set(r + 2, 1, "CORRECT", "example")
    s.set(r + 2, 2, "الحنين والشوق", "example")
    s.set(r + 2, 3, NONE_AR, "example")
    s.set(r + 2, 4, rtl("البكاء هنا شوق إلى غائب يُرجى لقاؤه، لا حزن على ميت."), "example")
    s.merges.append(f"D{r + 2}:E{r + 2}")
    s.heights[r + 2] = 32

    # sheet 2: the eight literary emotions
    e = book.add_sheet(SHEET_EMOTIONS)
    e.widths = {1: 20, 2: 20, 3: 40, 4: 40, 5: 44, 6: 30}
    for c, h in enumerate(["الإحساس", "المعرّف (id)", "التعريف", "يشمل", "لا يشمل", "مثال وصفي"], 1):
        e.set(1, c, h, "header")
    e.freeze = (2, 1)
    for i, label_id in enumerate(emotion_ids, 2):
        entry = taxonomy.labels[label_id]
        e.set(i, 1, entry["name_ar"], "subtitle")
        e.set(i, 2, label_id, "text")
        e.set(i, 3, rtl(entry["definition_ar"]), "text")
        e.set(i, 4, rtl("؛ ".join(entry["include_ar"])), "text")
        e.set(i, 5, rtl("؛ ".join(entry["exclude_ar"])), "text")
        e.set(i, 6, rtl("؛ ".join(x.get("text_ar", "") for x in entry["examples"])), "text")
        e.heights[i] = 48
    note_row = len(emotion_ids) + 3
    e.set(note_row, 1, "ملاحظة", "subtitle")
    e.set(note_row, 2, rtl("القائمة ثمانية أحاسيس فقط في الإصدار الأول. الحب والتأمل غير موجودين فيها؛ إن غلب أحدهما على بيت فاختاري REJECT أو UNSURE واكتبي ذلك في الملاحظة."), "text")
    e.merges.append(f"B{note_row}:F{note_row}")
    e.heights[note_row] = 36

    # sheet 3: review
    v = book.add_sheet(SHEET_REVIEW)
    v.landscape = True
    for field, header, width, _ in columns:
        v.set(1, col[field], header_text(field, header), "header")
        v.widths[col[field]] = width
    v.heights[1] = 48
    for i, row in enumerate(rows, 2):
        for field, _, _, style in columns:
            v.set(i, col[field], row[field][1], style)
        v.heights[i] = _row_height(row, columns)
    v.freeze = (2, 3)
    v.autofilter = f"A1:{col_letter(len(columns))}{last}"
    v.validations = [
        (decision_range, list(DECISIONS), "القرار", "ACCEPT أوافق، CORRECT أصحح، REJECT أرفض، UNSURE غير متأكدة",
         "قيمة غير صحيحة", "اختاري من القائمة: ACCEPT أو CORRECT أو REJECT أو UNSURE"),
        (f"{col_letter(col['corrected_primary'])}2:{col_letter(col['corrected_primary'])}{last}", lit_names,
         "الأساسي المصحح", "عند CORRECT فقط: اختاري الإحساس الأساسي الصحيح", "قيمة غير صحيحة",
         "اختاري أحد الأحاسيس الثمانية من القائمة"),
        (f"{col_letter(col['corrected_secondary'])}2:{col_letter(col['corrected_secondary'])}{last}",
         lit_names + [NONE_AR], "الثانوي المصحح", "عند CORRECT فقط: إحساس ثانوي واحد أو «لا يوجد»",
         "قيمة غير صحيحة", "اختاري من القائمة أو «لا يوجد»"),
    ]
    if visual:
        v.validations.append((f"{col_letter(col['visual_decision'])}2:{col_letter(col['visual_decision'])}{last}",
                              list(VISUAL_DECISIONS), "قرار الوسم البصري",
                              "ACCEPT الوسوم صحيحة، REJECT غير صحيحة، UNSURE غير متأكدة", "قيمة غير صحيحة",
                              "اختاري من القائمة: ACCEPT أو REJECT أو UNSURE"))
    book.defined_names.append(("_xlnm._FilterDatabase", 2, True, f"'{SHEET_REVIEW}'!$A$1:${col_letter(len(columns))}${last}"))
    book.active = 0
    book.save(path)


# --------------------------------------------------------------------------------------------- reading/checking
def read_review(path):
    """Read a returned sheet (.xlsx or .csv) into [{field: value}] keyed by contract field names."""
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return [dict(r) for r in csv.DictReader(fh)]
    sheets = read_workbook(path)
    if SHEET_REVIEW not in sheets:
        raise ValueError(f"sheet {SHEET_REVIEW!r} not found")
    rows = sheets[SHEET_REVIEW]
    header = rows.get(1, {})
    fields = {}
    for letters, text in header.items():
        match = re.search(r"\(([a-z_]+)\)\s*$", str(text or ""))
        if match:
            fields[letters] = match.group(1)
    out = []
    for r in sorted(k for k in rows if k > 1):
        item = {fields[c]: ("" if v is None else v) for c, v in rows[r].items() if c in fields}
        if any(str(x).strip() for x in item.values()):
            out.append(item)
    return out


def _to_id(value, taxonomy, allow_none):
    value = str(value or "").strip()
    if not value:
        return ""
    if allow_none and value == NONE_AR:
        return NONE_AR
    if taxonomy.layer(value) == "lit_emotion":
        return value
    for label_id in taxonomy.ids("lit_emotion"):
        if taxonomy.labels[label_id]["name_ar"] == value:
            return label_id
    return None


def check_review(rows, records, final=False, taxonomy=None, visual=False):
    """Return (issues, normalized rows). issues: [(verse_id, field, message)].
    visual=True also checks the visual decision column of P1+ packages."""
    taxonomy = taxonomy or load_taxonomy()
    by_id = {r["verse_id"]: r for r in records}
    issues, seen, normalized = [], set(), []
    for row in rows:
        verse_id = str(row.get("verse_id", "")).strip()
        if verse_id not in by_id:
            issues.append((verse_id or "?", "verse_id", "unknown verse_id"))
            continue
        if verse_id in seen:
            issues.append((verse_id, "verse_id", "row appears twice"))
        seen.add(verse_id)
        if str(row.get("text_original", "")) != by_id[verse_id]["text_original"]:
            issues.append((verse_id, "text_original", "verse text was changed; it must stay exactly as in APCD"))
        decision = str(row.get("decision", "") or "").strip().upper()
        note = str(row.get("note", "") or "").strip()
        primary = _to_id(row.get("corrected_primary"), taxonomy, allow_none=False)
        secondary = _to_id(row.get("corrected_secondary"), taxonomy, allow_none=True)
        if decision and decision not in DECISIONS:
            issues.append((verse_id, "decision", f"{decision!r} is not one of {DECISIONS}"))
        if final and not decision:
            issues.append((verse_id, "decision", "missing decision"))
        if primary is None:
            issues.append((verse_id, "corrected_primary", "not one of the eight literary emotions"))
        if secondary is None:
            issues.append((verse_id, "corrected_secondary", "not one of the eight literary emotions or «لا يوجد»"))
        if decision == "CORRECT" and not (primary or secondary):
            issues.append((verse_id, "corrected_primary", "CORRECT needs a corrected primary or secondary emotion"))
        if decision in ("ACCEPT", "REJECT", "UNSURE") and (primary or secondary):
            issues.append((verse_id, "corrected_primary", f"{decision} rows leave the correction columns empty"))
        if decision in ("REJECT", "UNSURE") and not note:
            issues.append((verse_id, "note", f"{decision} needs a short note"))
        if note and len(note.split()) > NOTE_MAX_WORDS:
            issues.append((verse_id, "note", f"note has {len(note.split())} words (max {NOTE_MAX_WORDS})"))
        if primary and secondary and primary == secondary:
            issues.append((verse_id, "corrected_secondary", "must differ from the corrected primary"))
        item = {"verse_id": verse_id, "decision": decision, "corrected_primary": primary or "",
                "corrected_secondary": secondary or "", "note": note}
        if visual:
            visual_decision = str(row.get("visual_decision", "") or "").strip().upper()
            if visual_decision and visual_decision not in VISUAL_DECISIONS:
                issues.append((verse_id, "visual_decision", f"{visual_decision!r} is not one of {VISUAL_DECISIONS}"))
            if final and not visual_decision:
                issues.append((verse_id, "visual_decision", "missing visual decision"))
            if visual_decision in ("REJECT", "UNSURE") and not note:
                issues.append((verse_id, "note", f"visual {visual_decision} needs a short note"))
            item["visual_decision"] = visual_decision
        normalized.append(item)
    for verse_id in by_id:
        if verse_id not in seen:
            issues.append((verse_id, "verse_id", "row missing from the returned sheet"))
    return issues, normalized


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check or export a returned review sheet.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("path")
    check.add_argument("--final", action="store_true", help="every row must carry a decision")
    check.add_argument("--drafts", default=os.path.join("poetry_corpus", "records", "p0_ai_drafts_v1.jsonl"))
    export = sub.add_parser("export-csv")
    export.add_argument("path")
    export.add_argument("out")
    export.add_argument("--drafts", default=os.path.join("poetry_corpus", "records", "p0_ai_drafts_v1.jsonl"))
    args = parser.parse_args(argv)
    records = [r for _, r in load_jsonl(args.drafts)[0]]
    rows = read_review(args.path)
    issues, normalized = check_review(rows, records, final=getattr(args, "final", False))
    for verse_id, field, message in issues:
        print(f"{verse_id}\t{field}\t{message}")
    if args.command == "export-csv":
        with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["verse_id", "decision", "corrected_primary",
                                                    "corrected_secondary", "note"])
            writer.writeheader()
            writer.writerows(normalized)
    decided = sum(1 for r in normalized if r["decision"])
    print(json.dumps({"rows": len(normalized), "decided": decided, "issues": len(issues)}), file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
