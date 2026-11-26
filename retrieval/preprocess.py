"""Arabic preprocessing for the retrieval representation (RETRIEVAL_METHOD.md section 1).

`text_original` is never modified: these functions build a separate normalized representation that is used
only for TF-IDF matching. Display always uses the record's original text.

Variants:
    N0  Unicode NFC; remove diacritics (U+064B-U+0652, U+0670) and tatweel (U+0640); fold alef forms
        (U+0623, U+0625, U+0622, U+0671) to bare alef; keep alef maqsura and ta marbuta; remove
        punctuation; collapse whitespace (the 4-space hemistich gap becomes one space).
    N1  N0 + strip the definite article, alone or with an attached particle (ال وال بال كال فال لل),
        only when at least 3 letters remain.  (default)
    N2  N1 + strip one single-letter proclitic (و ف ب ك ل), only when at least 3 letters remain and the
        token is not protected (taxonomy query terms and the words in PROTECTED_EXTRA).

No root stemming and no lemmatization are used (ISRI-style roots conflate unrelated words).
"""
import re
import unicodedata

VARIANTS = ("N0", "N1", "N2")
DEFAULT_VARIANT = "N1"

TATWEEL = "ـ"
_DIACRITICS = {chr(c) for c in range(0x064B, 0x0653)} | {"ٰ"}
_ALEF_FOLD = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}
MIN_STEM_LETTERS = 3

# Longest prefixes first, so "وال" is tried before "ال".
ARTICLE_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال")
PROCLITICS = ("و", "ف", "ب", "ك", "ل")

# Negations are always kept: they reverse the meaning of a verse.
NEGATIONS = frozenset({"لا", "ما", "لم", "لن", "ليس"})

# A small list of particles (written in their N0-normalized form). Kept deliberately short: the lecture warns
# that stop-word removal is "not always recommended (task-dependent)".
STOP_WORDS = frozenset({
    "من", "في", "على", "الى", "عن", "او", "ثم", "قد", "لقد", "ان", "اذا", "اذ", "يا", "هل", "بل",
    "حتى", "مع", "كي", "لكي", "و", "ف", "ب", "ل", "ك",
}) - NEGATIONS

# Words that the N2 proclitic rule would destroy (فراق -> راق, وداع -> داع, وادي -> ادي, بكاء -> كاء).
PROTECTED_EXTRA = ("فراق", "وداع", "وادي", "بكاء")

_SPACE = re.compile(r"\s+")


def normalize(text):
    """N0 normalization of a string (no tokenization, no prefix stripping)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        if ch in _DIACRITICS or ch == TATWEEL:
            continue
        ch = _ALEF_FOLD.get(ch, ch)
        cat = unicodedata.category(ch)
        if cat == "Mn" or cat == "Cf":
            # Any other combining mark or invisible format character (ZWNJ, BOM) is dropped, never turned into
            # a space, so that it cannot split a word in two.
            continue
        if cat[0] in "LN":
            out.append(ch)
        else:
            out.append(" ")  # punctuation, symbols, whitespace
    return _SPACE.sub(" ", "".join(out)).strip()


def strip_article(token):
    """N1 rule: remove the definite article (with an attached particle) if at least 3 letters remain."""
    for prefix in ARTICLE_PREFIXES:
        if token.startswith(prefix) and len(token) - len(prefix) >= MIN_STEM_LETTERS:
            return token[len(prefix):]
    return token


def strip_proclitic(token, protected=frozenset()):
    """N2 rule: remove one single-letter proclitic if at least 3 letters remain and the token is not protected."""
    if token in protected:
        return token
    if token[:1] in PROCLITICS and len(token) - 1 >= MIN_STEM_LETTERS:
        return token[1:]
    return token


def _protected_default():
    words = set()
    for w in PROTECTED_EXTRA:
        words.add(strip_article(normalize(w)))
    try:  # taxonomy query terms are protected as well (contracts/ is standard library only)
        from contracts.taxonomy import load_taxonomy
        for label in load_taxonomy().labels.values():
            for term in label.get("query_terms_ar") or []:
                for tok in normalize(term).split():
                    words.add(strip_article(tok))
    except (OSError, ValueError, ImportError):
        pass
    return frozenset(words)


PROTECTED = _protected_default()


def tokenize(text, variant=DEFAULT_VARIANT, stop_words=True, protected=None):
    """Normalize and split `text` into retrieval tokens for variant N0, N1 or N2."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    protected = PROTECTED if protected is None else protected
    tokens = []
    for tok in normalize(text).split():
        if stop_words and tok in STOP_WORDS:
            continue
        if variant in ("N1", "N2"):
            tok = strip_article(tok)
        if variant == "N2":
            tok = strip_proclitic(tok, protected)
        if stop_words and tok in STOP_WORDS:
            continue
        tokens.append(tok)
    return tokens
