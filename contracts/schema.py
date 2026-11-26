"""Minimal declarative schema checker shared by all contracts (Python standard library only)."""
import math
import re

ERROR_CODES = (
    "E_REQUIRED",               # required field missing or empty
    "E_TYPE",                   # wrong JSON type, null where not allowed, or unreadable JSON
    "E_ENUM",                   # value outside the allowed set
    "E_FORMAT",                 # value does not match the required format (sha256, uuid4, path, id ...)
    "E_RANGE",                  # number, length, word count or item count out of range
    "E_UNKNOWN_FIELD",          # field not defined by the contract
    "E_UNKNOWN_ID",             # taxonomy id unknown, from the wrong layer, or not exposed
    "E_VERSION",                # schema/taxonomy version invalid or unsupported
    "E_SPAN",                   # evidence span offsets or text do not match the original text
    "E_APCD_ROW",               # APCD row number invalid or absent from the zip
    "E_APCD_TEXT",              # verse text/metadata differs from APCD, or text hash mismatch
    "E_DISPLAY_RULE",           # derived display flag stored, or a non-displayable verse returned
    "E_STATUS_CONFLICT",        # fields contradict each other
    "E_DUP_ID",                 # duplicate identifier
    "E_SPLIT_LEAK",             # the same or a near-duplicate image appears in more than one split
    "E_FIXTURE_IN_PRODUCTION",  # fixture or development (unreviewed) data used in production mode
)


class Issue:
    __slots__ = ("code", "path", "message")

    def __init__(self, code, path, message):
        if code not in ERROR_CODES:
            raise ValueError(f"unknown error code {code}")
        self.code, self.path, self.message = code, path or "$", message

    def __str__(self):
        return f"{self.code}\t{self.path}\t{self.message}"

    def __repr__(self):
        return f"Issue({self.code!r}, {self.path!r}, {self.message!r})"


def _is_relpath(value):
    return (bool(value) and not value.startswith("/") and "\\" not in value
            and ".." not in value.split("/") and not value.endswith("/"))


FORMATS = {
    "semver": re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"),
    "version": re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z.-]+)?"),
    "sha256": re.compile(r"[0-9a-f]{64}"),
    "uuid4": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"),
    "date": re.compile(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"),
    "datetime": re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})"),
    "verse_id": re.compile(r"pv:verse:\d{6}"),
    "image_id": re.compile(r"img:[a-z0-9_]+:[A-Za-z0-9_.-]+"),
    "evidence_id": re.compile(r"ev:[a-z0-9_]+"),
    "poem_id": re.compile(r"hist:poem:[a-z0-9_]+"),
    "poet_id": re.compile(r"hist:poet:[a-z0-9_]+"),
    "taxonomy_id": re.compile(r"[a-z_]+\.[a-z0-9_]+"),
    "relpath": _is_relpath,
}


def matches(fmt, value):
    rule = FORMATS[fmt]
    return rule(value) if callable(rule) else bool(rule.fullmatch(value))


def is_semver(value):
    return isinstance(value, str) and matches("semver", value)


def major(version):
    return int(version.split(".")[0])


def join(path, name):
    if isinstance(name, int):
        return f"{path}[{name}]"
    return f"{path}.{name}" if path else name


class F:
    """Field specification.

    kind: "str", "id" (taxonomy id), "int", "num", "bool", "list", "obj" (fixed fields) or "map" (dynamic keys).
    layers (for "id"): allowed taxonomy layers; the pseudo-layer "tag_exposed" accepts exposed tags only.
    """

    def __init__(self, kind, *, required=True, nullable=False, enum=None, fmt=None, min=None, max=None,
                 exclusive_min=False, items=None, fields=None, keys=None, values=None, min_items=None,
                 max_items=None, layers=None, allow_empty=False, max_words=None):
        self.kind, self.required, self.nullable = kind, required, nullable
        self.enum, self.fmt, self.min, self.max, self.exclusive_min = enum, fmt, min, max, exclusive_min
        self.items, self.fields, self.keys, self.values = items, fields, keys, values
        self.min_items, self.max_items = min_items, max_items
        self.layers, self.allow_empty, self.max_words = layers, allow_empty, max_words


def check_fields(obj, fields, path, ctx, issues):
    """Check a dict against {name: F}: required fields, unknown fields and every value."""
    for name, spec in fields.items():
        if name not in obj:
            if spec.required:
                issues.append(Issue("E_REQUIRED", join(path, name), "missing required field"))
            continue
        check(obj[name], spec, join(path, name), ctx, issues)
    for name in obj:
        if name not in fields:
            issues.append(Issue("E_UNKNOWN_FIELD", join(path, name), "field is not defined by the contract"))


def check(value, spec, path, ctx, issues):
    if value is None:
        if not spec.nullable:
            issues.append(Issue("E_TYPE", path, "null is not allowed"))
        return
    kind = spec.kind
    if kind in ("str", "id"):
        _check_str(value, spec, path, ctx, issues)
    elif kind == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            issues.append(Issue("E_TYPE", path, f"expected integer, got {type(value).__name__}"))
            return
        _check_range(value, spec, path, issues)
    elif kind == "num":
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or (isinstance(value, float) and not math.isfinite(value))):
            issues.append(Issue("E_TYPE", path, f"expected finite number, got {value!r}"))
            return
        _check_range(value, spec, path, issues)
    elif kind == "bool":
        if not isinstance(value, bool):
            issues.append(Issue("E_TYPE", path, f"expected boolean, got {type(value).__name__}"))
    elif kind == "list":
        if not isinstance(value, list):
            issues.append(Issue("E_TYPE", path, f"expected list, got {type(value).__name__}"))
            return
        if spec.min_items is not None and len(value) < spec.min_items:
            issues.append(Issue("E_RANGE", path, f"expected at least {spec.min_items} item(s), got {len(value)}"))
        if spec.max_items is not None and len(value) > spec.max_items:
            issues.append(Issue("E_RANGE", path, f"expected at most {spec.max_items} item(s), got {len(value)}"))
        if spec.items is not None:
            for i, item in enumerate(value):
                check(item, spec.items, join(path, i), ctx, issues)
    elif kind == "obj":
        if not isinstance(value, dict):
            issues.append(Issue("E_TYPE", path, f"expected object, got {type(value).__name__}"))
            return
        check_fields(value, spec.fields or {}, path, ctx, issues)
    elif kind == "map":
        if not isinstance(value, dict):
            issues.append(Issue("E_TYPE", path, f"expected object, got {type(value).__name__}"))
            return
        for key, item in value.items():
            if spec.keys is not None:
                check(key, spec.keys, join(path, key), ctx, issues)
            if spec.values is not None:
                check(item, spec.values, join(path, key), ctx, issues)
    else:  # pragma: no cover - programming error
        raise ValueError(f"unknown field kind {kind}")


def _check_range(value, spec, path, issues):
    if spec.min is not None:
        if spec.exclusive_min and value <= spec.min:
            issues.append(Issue("E_RANGE", path, f"must be > {spec.min}, got {value}"))
        elif value < spec.min:
            issues.append(Issue("E_RANGE", path, f"must be >= {spec.min}, got {value}"))
    if spec.max is not None and value > spec.max:
        issues.append(Issue("E_RANGE", path, f"must be <= {spec.max}, got {value}"))


def _check_str(value, spec, path, ctx, issues):
    if not isinstance(value, str):
        issues.append(Issue("E_TYPE", path, f"expected string, got {type(value).__name__}"))
        return
    if not value.strip():
        if not spec.allow_empty:
            issues.append(Issue("E_REQUIRED", path, "empty string"))
        return
    if spec.enum is not None and value not in spec.enum:
        issues.append(Issue("E_ENUM", path, f"{value!r} is not one of {sorted(spec.enum)}"))
        return
    if spec.fmt and not matches(spec.fmt, value):
        code = "E_VERSION" if spec.fmt in ("semver", "version") else "E_FORMAT"
        issues.append(Issue(code, path, f"{value!r} is not a valid {spec.fmt}"))
        return
    if spec.max_words is not None and len(value.split()) > spec.max_words:
        issues.append(Issue("E_RANGE", path, f"at most {spec.max_words} words, got {len(value.split())}"))
    if spec.kind == "id":
        check_taxonomy_id(value, spec.layers, path, ctx, issues)


def check_taxonomy_id(value, layers, path, ctx, issues):
    if not matches("taxonomy_id", value):
        issues.append(Issue("E_FORMAT", path, f"{value!r} is not a taxonomy id (<layer>.<name>)"))
        return
    taxonomy = getattr(ctx, "taxonomy", None)
    if taxonomy is None:
        return
    layer = taxonomy.layer(value)
    if layer is None:
        issues.append(Issue("E_UNKNOWN_ID", path, f"{value!r} is not in taxonomy {taxonomy.version}"))
        return
    if not layers or layer in layers:
        return
    if layer == "tag" and "tag_exposed" in layers:
        if value not in taxonomy.exposed_tags:
            issues.append(Issue("E_UNKNOWN_ID", path, f"{value!r} is not an exposed tag in taxonomy {taxonomy.version}"))
        return
    allowed = ", ".join(layers)
    issues.append(Issue("E_UNKNOWN_ID", path, f"{value!r} belongs to layer {layer!r}; expected {allowed}"))
