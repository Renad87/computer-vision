"""Read APCD rows verbatim from the original zip (Python standard library only; the zip is never modified).

Row numbers are 0-based data-row indices of the CSV with the header excluded. This is the same convention
as scripts/locate_verses.py in the original Poetry-Vision project ("apcd:row:<n>").

Where the zip is looked up (first match wins; nothing is hard-coded to one machine):
  1. the PV_APCD_ZIP environment variable;
  2. <repo>/external/apcd/Arabic Poem Comprehensive Dataset (APCD).csv.zip
  3. <repo>/external/poetry_vision_old/Arabic Poem Comprehensive Dataset (APCD).csv.zip
"""
import csv
import io
import os
import zipfile

CSV_NAME = "Arabic Poem Comprehensive Dataset (APCD).csv"
ZIP_NAME = CSV_NAME + ".zip"
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CANDIDATES = (os.path.join(_REPO, "external", "apcd", ZIP_NAME),
               os.path.join(_REPO, "external", "poetry_vision_old", ZIP_NAME))


def _default_zip():
    if os.environ.get("PV_APCD_ZIP"):
        return os.environ["PV_APCD_ZIP"]
    return next((path for path in _CANDIDATES if os.path.isfile(path)), _CANDIDATES[0])


DEFAULT_ZIP = _default_zip()
COLUMNS = ("العصر", "الشاعر", "الديوان", "القافية", "البحر", "الشطر الايسر", "الشطر الايمن", "البيت")
# Column indices. In APCD the right hemistich (الشطر الايمن) is the first one (sadr) and the left one is the
# second (ajuz); the full verse column (البيت) is what poetry records store as `text_original`.
ERA, POET, DIWAN, RHYME, METER, SHATR_LEFT, SHATR_RIGHT, VERSE = range(8)


def available(zip_path=None):
    return os.path.isfile(zip_path or DEFAULT_ZIP)


def iter_rows(zip_path=None):
    """Yield (row_number, row) for every data row, streaming from the zip."""
    with zipfile.ZipFile(zip_path or DEFAULT_ZIP) as archive, archive.open(CSV_NAME) as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", errors="strict", newline=""))
        header = tuple(next(reader))
        if header != COLUMNS:
            raise ValueError(f"unexpected APCD header: {header!r}")
        for number, row in enumerate(reader):
            yield number, row


def get_rows(row_numbers, zip_path=None):
    """Return {row_number: row} for the requested rows; rows beyond the end of the file are absent."""
    wanted = {int(n) for n in row_numbers}
    found = {}
    if not wanted:
        return found
    last = max(wanted)
    rows = iter_rows(zip_path)
    try:
        for number, row in rows:
            if number in wanted:
                found[number] = row
            if number >= last:
                break
    finally:
        rows.close()
    return found
