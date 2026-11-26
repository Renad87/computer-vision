"""Shared taxonomy: loading, Places365 name mapping and validation of the `taxonomy` contract."""
import json
import os
import re

from .schema import F, Issue, check_fields, is_semver, join

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy", "taxonomy_v1.json")
LAYERS = ("scene", "scene_group", "tag", "img_emotion", "lit_emotion", "relation", "concept", "genre")
MODEL_LAYER_SIZES = {"scene": 17, "img_emotion": 8, "tag": 34}
QUERY_TERM_LAYERS = ("scene_group",)  # plus exposed tags


def normalize_places365_name(raw):
    """'/d/desert/sand', 'desert-sand' and 'Desert Sand' style names -> 'desert/sand' / 'desert_sand'."""
    name = raw.strip().lower()
    name = re.sub(r"^/[a-z]/", "", name)
    return name.replace("-", "/").replace(" ", "_")


class Taxonomy:
    def __init__(self, data):
        self.data = data if isinstance(data, dict) else {}
        d = self.data
        self.version = d.get("taxonomy_version")
        self.labels = {}
        for entry in d.get("labels") or []:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                self.labels.setdefault(entry["id"], entry)
        outputs = d.get("model_outputs") if isinstance(d.get("model_outputs"), dict) else {}
        self.class_order = {}
        self.external_names = {}
        for layer in MODEL_LAYER_SIZES:
            block = outputs.get(layer) if isinstance(outputs.get(layer), dict) else {}
            self.class_order[layer] = list(block.get("class_order") or [])
            self.external_names[layer] = list(block.get("external_names") or [])
        tag_block = outputs.get("tag") if isinstance(outputs.get("tag"), dict) else {}
        self.exposed_tags = list(tag_block.get("exposed") or [])
        self.scene_groups = d.get("scene_groups") if isinstance(d.get("scene_groups"), dict) else {}
        self.suggestion_basis = d.get("suggestion_basis")
        self.suggestion_pairs = {(m.get("from"), m.get("to")) for m in d.get("suggestion_map") or []
                                 if isinstance(m, dict)}
        self.user_only = set(d.get("user_only_lit_emotions") or [])
        self.relation_weights = dict(d.get("relation_weights") or {})
        self.pilot = d.get("pilot") if isinstance(d.get("pilot"), dict) else {}
        mapping = d.get("places365_mapping") if isinstance(d.get("places365_mapping"), dict) else {}
        self._place_to_scene = {}
        for key, cats in mapping.items():
            if isinstance(key, str) and key.startswith("scene.") and isinstance(cats, list):
                for cat in cats:
                    if isinstance(cat, str):
                        self._place_to_scene[normalize_places365_name(cat)] = key
        self._background = {normalize_places365_name(c) for c in mapping.get("background_for_scene_other") or []
                            if isinstance(c, str)}
        self._ood = {normalize_places365_name(c) for c in mapping.get("ood_excluded") or [] if isinstance(c, str)}

    def layer(self, label_id):
        entry = self.labels.get(label_id)
        return entry.get("layer") if entry else None

    def ids(self, layer):
        return [i for i, e in self.labels.items() if e.get("layer") == layer]

    def group_members(self, group_id):
        block = self.scene_groups.get(group_id) or {}
        return list(block.get("scenes") or []), list(block.get("tags") or [])

    def map_places365(self, raw):
        """Return (scene_label | None, scene_label_status) for a raw Places365 category name."""
        name = normalize_places365_name(raw)
        if name in self._place_to_scene:
            return self._place_to_scene[name], "labeled"
        if name in self._background:
            return "scene.other", "labeled"
        if name in self._ood:
            return None, "excluded_ood"
        return None, "unmapped"


def load_taxonomy(path=None):
    with open(path or DEFAULT_PATH, encoding="utf-8") as fh:
        return Taxonomy(json.load(fh))


# ---------------------------------------------------------------------------------------------- contract
_EXAMPLE = F("obj", fields={
    "type": F("str", enum={"description", "apcd_row"}),
    "text_ar": F("str", required=False),
    "apcd_row": F("int", required=False),
})
_ENTRY = {
    "id": F("str", fmt="taxonomy_id"),
    "layer": F("str", enum=set(LAYERS)),
    "name_ar": F("str"),
    "name_en": F("str"),
    "definition_ar": F("str"),
    "include_ar": F("list", items=F("str"), min_items=1),
    "exclude_ar": F("list", items=F("str"), min_items=1),
    "examples": F("list", items=_EXAMPLE, min_items=1),
    "provenance": F("obj", fields={"source": F("str"), "note": F("str")}),
    "query_terms_ar": F("list", required=False, items=F("str"), min_items=1),
}


def _output_block(with_exposed):
    fields = {"class_order": F("list", items=F("str")), "external_names": F("list", items=F("str")),
              "source": F("str")}
    if with_exposed:
        fields["exposed"] = F("list", items=F("str"), min_items=1)
    return F("obj", fields=fields)


TAXONOMY_DOC = {
    "schema_version": F("str", fmt="semver"),
    "taxonomy_version": F("str", fmt="semver"),
    "title_ar": F("str"),
    "build_notes": F("str", required=False),
    "layers": F("list", items=F("str", enum=set(LAYERS)), min_items=1),
    "labels": F("list", items=F("obj", fields=_ENTRY), min_items=1),
    "model_outputs": F("obj", fields={"scene": _output_block(False), "img_emotion": _output_block(False),
                                      "tag": _output_block(True)}),
    "scene_groups": F("map", keys=F("str", fmt="taxonomy_id"),
                      values=F("obj", fields={"scenes": F("list", items=F("str")),
                                              "tags": F("list", items=F("str"))})),
    "pilot": F("obj", fields={"scene_groups": F("list", items=F("str"), min_items=1),
                              "lit_emotions": F("list", items=F("str"), min_items=1)}),
    "suggestion_basis": F("str"),
    "suggestion_map": F("list", items=F("obj", fields={"from": F("str"), "to": F("str")})),
    "user_only_lit_emotions": F("list", items=F("str")),
    "relation_weights": F("map", keys=F("str"), values=F("num", min=0, max=1)),
    "symbolic_requires_permission": F("bool"),
    "places365_name_normalization": F("str"),
    "places365_mapping": F("map", keys=F("str"), values=F("list", items=F("str"))),
}


class _OwnContext:
    def __init__(self, taxonomy):
        self.taxonomy = taxonomy


def validate_taxonomy(doc, issues, supported_major=1):
    """Validate a taxonomy document against the contract; appends Issue objects to `issues`."""
    if not isinstance(doc, dict):
        issues.append(Issue("E_TYPE", "$", "taxonomy must be a JSON object"))
        return
    own = Taxonomy(doc)
    check_fields(doc, TAXONOMY_DOC, "", _OwnContext(own), issues)
    for key in ("schema_version", "taxonomy_version"):
        value = doc.get(key)
        if is_semver(value) and int(value.split(".")[0]) != supported_major:
            issues.append(Issue("E_VERSION", key, f"major version {value} is not supported (expected {supported_major}.x.x)"))

    def flag(code, path, message):
        issues.append(Issue(code, path, message))

    def expect(path, label_id, layers):
        layer = own.layer(label_id) if isinstance(label_id, str) else None
        if layer is None:
            flag("E_UNKNOWN_ID", path, f"{label_id!r} is not a label of this taxonomy")
            return False
        if layer not in layers:
            flag("E_UNKNOWN_ID", path, f"{label_id!r} belongs to layer {layer!r}; expected {', '.join(layers)}")
            return False
        return True

    labels = doc.get("labels") if isinstance(doc.get("labels"), list) else []
    seen = {}
    for i, entry in enumerate(labels):
        if not isinstance(entry, dict):
            continue
        path = join("labels", i)
        label_id, layer = entry.get("id"), entry.get("layer")
        if isinstance(label_id, str):
            if label_id in seen:
                flag("E_DUP_ID", join(path, "id"), f"duplicate id {label_id!r} (first at labels[{seen[label_id]}])")
            else:
                seen[label_id] = i
            if isinstance(layer, str) and label_id.split(".", 1)[0] != layer:
                flag("E_STATUS_CONFLICT", join(path, "layer"), f"id prefix of {label_id!r} does not match layer {layer!r}")
        needs_terms = layer in QUERY_TERM_LAYERS or label_id in own.exposed_tags
        if needs_terms and not entry.get("query_terms_ar"):
            flag("E_REQUIRED", join(path, "query_terms_ar"), "scene groups and exposed tags need query terms")
        for j, example in enumerate(entry.get("examples") or []):
            if not isinstance(example, dict):
                continue
            epath = join(join(path, "examples"), j)
            if example.get("type") == "description" and not example.get("text_ar"):
                flag("E_REQUIRED", join(epath, "text_ar"), "description examples need text_ar")
            if example.get("type") == "apcd_row":
                row = example.get("apcd_row")
                if not isinstance(row, int) or isinstance(row, bool) or row < 0:
                    flag("E_APCD_ROW", join(epath, "apcd_row"), "apcd_row must be an integer >= 0")

    declared = doc.get("layers") if isinstance(doc.get("layers"), list) else []
    if set(declared) != set(LAYERS):
        flag("E_STATUS_CONFLICT", "layers", f"layers must be exactly {list(LAYERS)}")
    for layer in LAYERS:
        if not own.ids(layer):
            flag("E_REQUIRED", "labels", f"no labels for layer {layer!r}")

    for layer, size in MODEL_LAYER_SIZES.items():
        path = join("model_outputs", layer)
        order = own.class_order[layer]
        if len(order) != size:
            flag("E_RANGE", join(path, "class_order"), f"expected {size} classes, got {len(order)}")
        if len(set(order)) != len(order):
            flag("E_DUP_ID", join(path, "class_order"), "duplicate class ids")
        for k, label_id in enumerate(order):
            expect(join(join(path, "class_order"), k), label_id, (layer,))
        if set(order) != set(own.ids(layer)):
            flag("E_STATUS_CONFLICT", join(path, "class_order"), f"class_order must cover every {layer} label exactly")
        if len(own.external_names[layer]) != len(order):
            flag("E_STATUS_CONFLICT", join(path, "external_names"), "external_names must align with class_order")
    for k, label_id in enumerate(own.exposed_tags):
        if label_id not in own.class_order["tag"]:
            flag("E_UNKNOWN_ID", join("model_outputs.tag.exposed", k), f"{label_id!r} is not a model tag")

    groups = own.scene_groups
    if set(groups) != set(own.ids("scene_group")):
        flag("E_STATUS_CONFLICT", "scene_groups", "scene_groups must define every scene_group label exactly once")
    owner = {}
    for group_id, block in groups.items():
        if not isinstance(block, dict):
            continue
        for k, scene in enumerate(block.get("scenes") or []):
            path = join(join(join("scene_groups", group_id), "scenes"), k)
            if not expect(path, scene, ("scene",)):
                continue
            if scene == "scene.other":
                flag("E_STATUS_CONFLICT", path, "scene.other has no retrieval group")
            if scene in owner:
                flag("E_STATUS_CONFLICT", path, f"{scene} already belongs to {owner[scene]}")
            owner[scene] = group_id
        for k, tag in enumerate(block.get("tags") or []):
            expect(join(join(join("scene_groups", group_id), "tags"), k), tag, ("tag",))

    for key, layer in (("scene_groups", "scene_group"), ("lit_emotions", "lit_emotion")):
        for k, label_id in enumerate(own.pilot.get(key) or []):
            expect(join(join("pilot", key), k), label_id, (layer,))

    sources = {}
    for k, pair in enumerate(doc.get("suggestion_map") or []):
        if not isinstance(pair, dict):
            continue
        path = join("suggestion_map", k)
        source, target = pair.get("from"), pair.get("to")
        expect(join(path, "from"), source, ("img_emotion",))
        expect(join(path, "to"), target, ("lit_emotion",))
        if source in sources:
            flag("E_DUP_ID", join(path, "from"), f"{source} is mapped twice")
        sources[source] = target
        if target in own.user_only:
            flag("E_STATUS_CONFLICT", join(path, "to"), f"{target} is user-only and may never be suggested")
    for k, label_id in enumerate(doc.get("user_only_lit_emotions") or []):
        expect(join("user_only_lit_emotions", k), label_id, ("lit_emotion",))

    if set(own.relation_weights) != set(own.ids("relation")):
        flag("E_STATUS_CONFLICT", "relation_weights", "relation_weights must define every relation label exactly")

    mapping = doc.get("places365_mapping") if isinstance(doc.get("places365_mapping"), dict) else {}
    required_keys = {s for s in own.ids("scene") if s != "scene.other"} | {"background_for_scene_other", "ood_excluded"}
    for key in sorted(required_keys - set(mapping)):
        flag("E_REQUIRED", join("places365_mapping", key), "missing Places365 list")
    for key in sorted(set(mapping) - required_keys):
        flag("E_UNKNOWN_FIELD", join("places365_mapping", key), "not a scene id or a known list name")
    where = {}
    for key, cats in mapping.items():
        for cat in cats if isinstance(cats, list) else []:
            if not isinstance(cat, str):
                continue
            name = normalize_places365_name(cat)
            if name in where and where[name] != key:
                flag("E_STATUS_CONFLICT", join("places365_mapping", key), f"{cat!r} also listed under {where[name]}")
            where[name] = key
