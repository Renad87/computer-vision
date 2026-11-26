"""Minimal .xlsx writer and reader (Python standard library only, no openpyxl).

Writer: inline strings, numbers, formulas with cached values, a fixed style palette, column widths, row
heights, right-to-left sheets, frozen panes, merged cells, an auto-filter and list data validations
(dropdowns). Output is deterministic: fixed timestamps, so the same input gives the same bytes.
Reader: cell values by sheet (shared, inline or formula strings, numbers, booleans).
"""
import re
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
FIXED_TIME = (2026, 11, 25, 0, 0, 0)

# style name -> (fontId, fillId, borderId, alignment attributes)
STYLE_ORDER = ["default", "title", "subtitle", "header", "text", "verse", "editable", "note", "number", "example"]
_FONTS = [
    '<font><sz val="11"/><name val="Arial"/><family val="2"/></font>',
    '<font><b/><sz val="11"/><name val="Arial"/><family val="2"/></font>',
    '<font><b/><sz val="16"/><name val="Arial"/><family val="2"/></font>',
    '<font><sz val="14"/><name val="Arial"/><family val="2"/></font>',
    '<font><i/><sz val="10"/><color rgb="FF595959"/><name val="Arial"/><family val="2"/></font>',
    '<font><b/><sz val="12"/><name val="Arial"/><family val="2"/></font>',
]
_FILLS = [
    '<fill><patternFill patternType="none"/></fill>',
    '<fill><patternFill patternType="gray125"/></fill>',
    '<fill><patternFill patternType="solid"><fgColor rgb="FFDDEBF7"/><bgColor indexed="64"/></patternFill></fill>',
    '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>',
    '<fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/><bgColor indexed="64"/></patternFill></fill>',
]
_BORDERS = [
    '<border><left/><right/><top/><bottom/><diagonal/></border>',
    '<border><left style="thin"><color rgb="FFBFBFBF"/></left><right style="thin"><color rgb="FFBFBFBF"/></right>'
    '<top style="thin"><color rgb="FFBFBFBF"/></top><bottom style="thin"><color rgb="FFBFBFBF"/></bottom>'
    '<diagonal/></border>',
]
_RTL_TOP = 'horizontal="right" vertical="top" wrapText="1" readingOrder="2"'
_XFS = {
    "default": (0, 0, 0, None),
    "title": (2, 0, 0, 'horizontal="right" vertical="center" readingOrder="2"'),
    "subtitle": (5, 0, 0, _RTL_TOP),
    "header": (1, 2, 1, 'horizontal="center" vertical="center" wrapText="1" readingOrder="2"'),
    "text": (0, 0, 1, _RTL_TOP),
    "verse": (3, 0, 1, _RTL_TOP),
    "editable": (0, 3, 1, _RTL_TOP),
    "note": (4, 0, 0, _RTL_TOP),
    "number": (0, 0, 1, 'horizontal="center" vertical="top"'),
    "example": (0, 4, 1, _RTL_TOP),
}


def col_letter(index):
    """1-based column index -> letters (1 -> A, 27 -> AA)."""
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def col_index(letters):
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch) - 64)
    return value


def _attr(value):
    return escape(str(value), {'"': "&quot;"})


def _text(value):
    # drop characters XML 1.0 cannot carry
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
    return escape(value)


class Sheet:
    def __init__(self, name, rtl=True):
        if len(name) > 31 or any(ch in name for ch in "[]:*?/\\"):
            raise ValueError(f"invalid sheet name {name!r}")
        self.name, self.rtl = name, rtl
        self.cells = {}          # (row, col) -> (kind, value, style, cached)
        self.widths = {}         # col -> width in characters
        self.heights = {}        # row -> height in points
        self.freeze = None       # (row, col) of the first unfrozen cell, e.g. (2, 3) = "C2"
        self.merges = []
        self.validations = []    # (sqref, values, prompt_title, prompt, error_title, error)
        self.autofilter = None   # "A1:S41"
        self.landscape = False

    def set(self, row, col, value, style="text"):
        if value is None or value == "":
            self.cells[(row, col)] = ("blank", None, style, None)
        elif isinstance(value, bool):
            raise TypeError("booleans are not supported")
        elif isinstance(value, (int, float)):
            self.cells[(row, col)] = ("number", value, style, None)
        else:
            self.cells[(row, col)] = ("string", str(value), style, None)

    def formula(self, row, col, expression, cached, style="number"):
        self.cells[(row, col)] = ("formula", expression.lstrip("="), style, cached)

    def extent(self):
        rows = [r for r, _ in self.cells] or [1]
        cols = [c for _, c in self.cells] or [1]
        return max(rows), max(cols)

    def xml(self, selected):
        style_index = {name: i for i, name in enumerate(STYLE_ORDER)}
        max_row, max_col = self.extent()
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               f'<worksheet xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">']
        if self.landscape:
            out.append('<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>')
        out.append(f'<dimension ref="A1:{col_letter(max_col)}{max_row}"/>')
        view_attrs = ('rightToLeft="1" ' if self.rtl else "") + ('tabSelected="1" ' if selected else "")
        view = f'<sheetView {view_attrs}workbookViewId="0">'
        if self.freeze:
            row, col = self.freeze
            x_split, y_split = col - 1, row - 1
            top_left = f"{col_letter(col)}{row}"
            if x_split and y_split:
                pane = "bottomRight"
            elif y_split:
                pane = "bottomLeft"
            else:
                pane = "topRight"
            split = (f'xSplit="{x_split}" ' if x_split else "") + (f'ySplit="{y_split}" ' if y_split else "")
            view += f'<pane {split}topLeftCell="{top_left}" activePane="{pane}" state="frozen"/>'
            view += f'<selection pane="{pane}" activeCell="{top_left}" sqref="{top_left}"/>'
        view += "</sheetView>"
        out.append(f"<sheetViews>{view}</sheetViews>")
        out.append('<sheetFormatPr defaultRowHeight="15"/>')
        if self.widths:
            out.append("<cols>" + "".join(
                f'<col min="{c}" max="{c}" width="{w}" customWidth="1"/>' for c, w in sorted(self.widths.items()))
                + "</cols>")
        out.append("<sheetData>")
        for row in range(1, max_row + 1):
            cells = sorted((c, v) for (r, c), v in self.cells.items() if r == row)
            if not cells and row not in self.heights:
                continue
            height = self.heights.get(row)
            attrs = f' ht="{height}" customHeight="1"' if height else ""
            out.append(f'<row r="{row}"{attrs}>')
            for col, (kind, value, style, cached) in cells:
                ref = f"{col_letter(col)}{row}"
                s = style_index[style]
                if kind == "blank":
                    out.append(f'<c r="{ref}" s="{s}"/>')
                elif kind == "number":
                    out.append(f'<c r="{ref}" s="{s}"><v>{value}</v></c>')
                elif kind == "formula":
                    out.append(f'<c r="{ref}" s="{s}"><f>{_text(value)}</f><v>{cached}</v></c>')
                else:
                    out.append(f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{_text(value)}</t></is></c>')
            out.append("</row>")
        out.append("</sheetData>")
        if self.autofilter:
            out.append(f'<autoFilter ref="{self.autofilter}"/>')
        if self.merges:
            out.append(f'<mergeCells count="{len(self.merges)}">'
                       + "".join(f'<mergeCell ref="{m}"/>' for m in self.merges) + "</mergeCells>")
        if self.validations:
            out.append(f'<dataValidations count="{len(self.validations)}">')
            for sqref, values, prompt_title, prompt, error_title, error in self.validations:
                listed = ",".join(values)
                if len(listed) > 255 or any(("," in v or '"' in v) for v in values):
                    raise ValueError("inline list validation must be <= 255 characters without commas or quotes")
                out.append(
                    f'<dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" '
                    f'errorStyle="stop" errorTitle="{_attr(error_title)}" error="{_attr(error)}" '
                    f'promptTitle="{_attr(prompt_title)}" prompt="{_attr(prompt)}" sqref="{sqref}">'
                    f'<formula1>"{_text(listed)}"</formula1></dataValidation>')
            out.append("</dataValidations>")
        out.append('<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>')
        if self.landscape:
            out.append('<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>')
        out.append("</worksheet>")
        return "".join(out)


class Workbook:
    def __init__(self, title="", creator="Poetry Vision"):
        self.sheets, self.title, self.creator = [], title, creator
        self.active = 0
        self.defined_names = []  # (name, local_sheet_index or None, hidden, value)

    def add_sheet(self, name, rtl=True):
        sheet = Sheet(name, rtl)
        self.sheets.append(sheet)
        return sheet

    def _styles(self):
        xfs = []
        for name in STYLE_ORDER:
            font, fill, border, align = _XFS[name]
            apply = f'applyFont="1" applyFill="{1 if fill else 0}" applyBorder="{1 if border else 0}"'
            if align:
                xfs.append(f'<xf numFmtId="0" fontId="{font}" fillId="{fill}" borderId="{border}" xfId="0" {apply} '
                           f'applyAlignment="1"><alignment {align}/></xf>')
            else:
                xfs.append(f'<xf numFmtId="0" fontId="{font}" fillId="{fill}" borderId="{border}" xfId="0" {apply}/>')
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<styleSheet xmlns="{NS_MAIN}">'
                f'<fonts count="{len(_FONTS)}">{"".join(_FONTS)}</fonts>'
                f'<fills count="{len(_FILLS)}">{"".join(_FILLS)}</fills>'
                f'<borders count="{len(_BORDERS)}">{"".join(_BORDERS)}</borders>'
                '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
                '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                "</styleSheet>")

    def _workbook(self):
        sheets = "".join(f'<sheet name="{_attr(s.name)}" sheetId="{i}" r:id="rId{i}"/>'
                         for i, s in enumerate(self.sheets, 1))
        names = ""
        if self.defined_names:
            names = "<definedNames>" + "".join(
                f'<definedName name="{_attr(n)}"'
                + (f' localSheetId="{local}"' if local is not None else "")
                + (' hidden="1"' if hidden else "") + f">{_text(value)}</definedName>"
                for n, local, hidden, value in self.defined_names) + "</definedNames>"
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}"><workbookPr/>'
                f'<bookViews><workbookView activeTab="{self.active}"/></bookViews>'
                f"<sheets>{sheets}</sheets>{names}"
                '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')

    def save(self, path):
        n = len(self.sheets)
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, n + 1))
        parts = {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                f"{overrides}"
                '<Override PartName="/xl/styles.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                '<Override PartName="/docProps/core.xml" '
                'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                '<Override PartName="/docProps/app.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                "</Types>"),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Relationships xmlns="{NS_PKG_REL}">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'officeDocument" Target="xl/workbook.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
                'core-properties" Target="docProps/core.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'extended-properties" Target="docProps/app.xml"/>'
                "</Relationships>"),
            "docProps/core.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f"<dc:title>{_text(self.title)}</dc:title><dc:creator>{_text(self.creator)}</dc:creator>"
                '<dcterms:created xsi:type="dcterms:W3CDTF">2026-11-25T00:00:00Z</dcterms:created>'
                "</cp:coreProperties>"),
            "docProps/app.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                "<Application>Poetry Vision stdlib xlsx writer</Application></Properties>"),
            "xl/workbook.xml": self._workbook(),
            "xl/_rels/workbook.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Relationships xmlns="{NS_PKG_REL}">'
                + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                          f'relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, n + 1))
                + f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                  'relationships/styles" Target="styles.xml"/></Relationships>'),
            "xl/styles.xml": self._styles(),
        }
        for i, sheet in enumerate(self.sheets, 1):
            parts[f"xl/worksheets/sheet{i}.xml"] = sheet.xml(selected=(i - 1 == self.active))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, text in parts.items():
                ET.fromstring(text.encode("utf-8"))  # every part must be well-formed XML
                info = zipfile.ZipInfo(name, FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, text.encode("utf-8"))


# --------------------------------------------------------------------------------------------- reader
def _q(tag):
    return f"{{{NS_MAIN}}}{tag}"


def _shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    strings = []
    for si in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(_q("si")):
        parts = []
        for child in si:
            if child.tag == _q("t"):
                parts.append(child.text or "")
            elif child.tag == _q("r"):
                parts.extend(t.text or "" for t in child.findall(_q("t")))
        strings.append("".join(parts))
    return strings


def read_workbook(path):
    """Return {sheet name: {row: {column letters: value}}} with strings, numbers (int when integral) or bools."""
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        shared = _shared_strings(archive)
        result = {}
        for sheet in workbook.find(_q("sheets")):
            target = targets[sheet.get(f"{{{NS_REL}}}id")]
            part = target.lstrip("/") if target.startswith("/") else "xl/" + target
            root = ET.fromstring(archive.read(part))
            rows = {}
            for cell in root.iter(_q("c")):
                match = re.fullmatch(r"([A-Z]+)(\d+)", cell.get("r") or "")
                if not match:
                    continue
                kind, v = cell.get("t"), cell.find(_q("v"))
                if kind == "s":
                    value = shared[int(v.text)] if v is not None else None
                elif kind == "inlineStr":
                    value = "".join(t.text or "" for t in cell.iter(_q("t")))
                elif kind in ("str", "e"):
                    value = v.text if v is not None else None
                elif kind == "b":
                    value = v is not None and v.text == "1"
                elif v is not None and v.text is not None:
                    number = float(v.text)
                    value = int(number) if number.is_integer() else number
                else:
                    value = None
                rows.setdefault(int(match.group(2)), {})[match.group(1)] = value
            result[sheet.get("name")] = rows
        return result


def read_validations(path, sheet_index):
    """Return [(sqref, formula1)] for the list validations of a sheet (1-based index)."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet_index}.xml"))
    return [(dv.get("sqref"), (dv.find(_q("formula1")).text or "")) for dv in root.iter(_q("dataValidation"))]
